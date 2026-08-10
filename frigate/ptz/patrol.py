"""Persistent storage for UI-managed PTZ patrol routes."""

import logging
import os
import tempfile

from ruamel.yaml import YAML

from frigate.config import PtzPatrolConfig
from frigate.const import CONFIG_DIR

logger = logging.getLogger(__name__)


def patrol_config_path() -> str:
    return os.environ.get(
        "PTZ_PATROL_CONFIG_FILE", os.path.join(CONFIG_DIR, "ptz_patrol.yml")
    )


def load_patrol_configs() -> dict[str, PtzPatrolConfig]:
    path = patrol_config_path()
    if not os.path.isfile(path):
        return {}

    yaml = YAML(typ="safe")
    try:
        with open(path) as config_file:
            raw = yaml.load(config_file) or {}
    except Exception as e:
        logger.error(f"Unable to read PTZ patrol configuration {path}: {e}")
        return {}

    configs = {}
    for camera, value in (raw.get("cameras") or {}).items():
        try:
            configs[camera] = PtzPatrolConfig.model_validate(value or {})
        except Exception as e:
            logger.error(f"Invalid PTZ patrol configuration for {camera}: {e}")
    return configs


def save_patrol_config(camera: str, patrol: PtzPatrolConfig) -> None:
    path = patrol_config_path()
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)

    data = {"cameras": {}}
    if os.path.isfile(path):
        with open(path) as config_file:
            data = yaml.load(config_file) or data
    data.setdefault("cameras", {})[camera] = patrol.model_dump()

    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(
        dir=directory, prefix=".ptz_patrol.", suffix=".yml"
    )
    try:
        with os.fdopen(descriptor, "w") as config_file:
            yaml.dump(data, config_file)
        os.replace(temporary_path, path)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)
