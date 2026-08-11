import asyncio
import os
import tempfile
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import ValidationError

from frigate.config import PtzPatrolConfig, PtzPatrolStepConfig
from frigate.ptz.onvif import OnvifController
from frigate.ptz.patrol import load_patrol_configs, save_patrol_config


def patrol_config(enabled=False, object_tracking=False, steps=None):
    return PtzPatrolConfig(
        enabled=enabled, object_tracking=object_tracking, steps=steps or []
    )


class TestPtzPatrolConfig(IsolatedAsyncioTestCase):
    def test_enabled_patrol_requires_two_steps(self):
        with self.assertRaises(ValidationError):
            patrol_config(
                enabled=True,
                steps=[PtzPatrolStepConfig(preset="door", dwell=10)],
            )

    def test_dwell_is_bounded(self):
        with self.assertRaises(ValidationError):
            PtzPatrolStepConfig(preset="door", dwell=0)


class TestPtzPatrolStore(TestCase):
    def test_round_trip_separate_patrol_file(self):
        config = patrol_config(
            enabled=True,
            steps=[
                PtzPatrolStepConfig(preset="door", dwell=5),
                PtzPatrolStepConfig(preset="driveway", dwell=8),
            ],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "ptz_patrol.yml")
            with patch.dict(os.environ, {"PTZ_PATROL_CONFIG_FILE": path}):
                save_patrol_config("front", config)
                loaded = load_patrol_configs()

        self.assertEqual(loaded["front"], config)


class TestOnvifPatrolController(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.controller = OnvifController.__new__(OnvifController)
        self.controller.loop = asyncio.get_running_loop()
        self.controller.patrol_retry_interval = 0
        self.controller.patrol_tasks = {}
        self.controller.patrol_state = {
            "front": {
                "running": False,
                "paused_for_tracking": False,
                "current_preset": None,
                "last_error": None,
            }
        }
        self.controller.cams = {
            "front": {
                "init": True,
                "features": ["pt"],
                "presets": {"door": "1", "driveway": "2"},
                "move_request": SimpleNamespace(ProfileToken="profile"),
                "ptz": MagicMock(),
            }
        }
        self.controller.config = SimpleNamespace(
            cameras={
                "front": SimpleNamespace(
                    onvif=SimpleNamespace(
                        patrol=patrol_config(),
                        autotracking=SimpleNamespace(
                            enabled=False, enabled_in_config=True
                        ),
                    )
                )
            }
        )
        self.controller.ptz_metrics = {
            "front": SimpleNamespace(autotracker_enabled=SimpleNamespace(value=False))
        }
        self.controller._ensure_initialized = AsyncMock()

    async def test_configure_rejects_unknown_presets(self):
        config = patrol_config(
            steps=[
                PtzPatrolStepConfig(preset="door", dwell=5),
                PtzPatrolStepConfig(preset="yard", dwell=5),
            ]
        )

        with self.assertRaisesRegex(ValueError, "yard"):
            await self.controller.configure_patrol("front", config)

    async def test_configure_starts_enabled_patrol(self):
        config = patrol_config(
            enabled=True,
            steps=[
                PtzPatrolStepConfig(preset="door", dwell=5),
                PtzPatrolStepConfig(preset="driveway", dwell=5),
            ],
        )
        self.controller._start_patrol = AsyncMock()

        info = await self.controller.configure_patrol("front", config)

        self.controller._start_patrol.assert_awaited_once_with("front")
        self.assertTrue(info["patrol"]["enabled"])
        self.assertEqual(info["patrol"]["steps"][0]["preset"], "door")

    async def test_patrol_cycles_from_first_step(self):
        self.controller.config.cameras["front"].onvif.patrol = patrol_config(
            enabled=True,
            steps=[
                PtzPatrolStepConfig(preset="door", dwell=1),
                PtzPatrolStepConfig(preset="driveway", dwell=1),
            ],
        )
        self.controller._move_to_preset = AsyncMock()

        await self.controller._start_patrol("front")
        await asyncio.sleep(0)
        await self.controller._stop_patrol("front")

        self.controller._move_to_preset.assert_awaited_once_with("front", "door")
        self.assertFalse(self.controller.patrol_state["front"]["running"])

    async def test_tracking_pause_resumes_running_patrol(self):
        self.controller.config.cameras["front"].onvif.patrol = patrol_config(
            enabled=True,
            steps=[
                PtzPatrolStepConfig(preset="door", dwell=1),
                PtzPatrolStepConfig(preset="driveway", dwell=1),
            ],
        )
        self.controller._move_to_preset = AsyncMock()

        await self.controller._start_patrol("front")
        await asyncio.sleep(0)
        await self.controller.pause_patrol_for_tracking("front")

        self.assertFalse(self.controller.patrol_state["front"]["running"])
        self.assertTrue(self.controller.patrol_state["front"]["paused_for_tracking"])

        resumed = await self.controller.resume_patrol_after_tracking("front")
        await asyncio.sleep(0)
        await self.controller._stop_patrol("front")

        self.assertTrue(resumed)
        self.assertEqual(self.controller._move_to_preset.await_count, 2)

    async def test_manual_stop_clears_tracking_resume_intent(self):
        self.controller.patrol_state["front"]["paused_for_tracking"] = True

        await self.controller._stop_patrol("front")

        self.assertFalse(self.controller.patrol_state["front"]["paused_for_tracking"])
        self.assertFalse(await self.controller.resume_patrol_after_tracking("front"))

    async def test_configure_object_tracking_updates_runtime_toggle(self):
        config = patrol_config(
            object_tracking=True,
            steps=[
                PtzPatrolStepConfig(preset="door", dwell=5),
                PtzPatrolStepConfig(preset="driveway", dwell=5),
            ],
        )

        await self.controller.configure_patrol("front", config)

        self.assertTrue(
            self.controller.config.cameras["front"].onvif.autotracking.enabled
        )
        self.assertTrue(self.controller.ptz_metrics["front"].autotracker_enabled.value)

    async def test_remove_rejects_preset_used_by_patrol(self):
        self.controller.config.cameras["front"].onvif.patrol = patrol_config(
            steps=[PtzPatrolStepConfig(preset="door", dwell=5)]
        )

        with self.assertRaisesRegex(ValueError, "configured patrol"):
            await self.controller.remove_preset("front", "door")

    async def test_patrol_reconnects_and_resumes_after_move_failure(self):
        self.controller.config.cameras["front"].onvif.patrol = patrol_config(
            enabled=True,
            steps=[
                PtzPatrolStepConfig(preset="door", dwell=1),
                PtzPatrolStepConfig(preset="driveway", dwell=1),
            ],
        )
        self.controller._move_to_preset = AsyncMock(
            side_effect=[ConnectionError("camera offline"), None]
        )
        self.controller._restore_patrol_connection = AsyncMock()

        await self.controller._start_patrol("front")
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await self.controller._stop_patrol("front")

        self.controller._restore_patrol_connection.assert_awaited_once_with("front")
        self.assertEqual(self.controller._move_to_preset.await_count, 2)

    async def test_restore_patrol_connection_retries_until_initialized(self):
        self.controller._init_onvif = AsyncMock(side_effect=[False, True])

        await self.controller._restore_patrol_connection("front")

        self.assertEqual(self.controller._init_onvif.await_count, 2)
        self.assertIsNone(self.controller.patrol_state["front"]["last_error"])
