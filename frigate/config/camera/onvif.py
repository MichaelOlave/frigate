from enum import Enum
from typing import Optional, Union

from pydantic import Field, field_validator, model_validator

from ..base import FrigateBaseModel
from ..env import EnvString
from .objects import DEFAULT_TRACKED_OBJECTS

__all__ = [
    "OnvifConfig",
    "PtzAutotrackConfig",
    "PtzPatrolConfig",
    "PtzPatrolStepConfig",
    "ZoomingModeEnum",
]


class ZoomingModeEnum(str, Enum):
    disabled = "disabled"
    absolute = "absolute"
    relative = "relative"


class PtzAutotrackConfig(FrigateBaseModel):
    enabled: bool = Field(default=False, title="Enable PTZ object autotracking.")
    calibrate_on_startup: bool = Field(
        default=False, title="Perform a camera calibration when Frigate starts."
    )
    zooming: ZoomingModeEnum = Field(
        default=ZoomingModeEnum.disabled, title="Autotracker zooming mode."
    )
    zoom_factor: float = Field(
        default=0.3,
        title="Zooming factor (0.1-0.75).",
        ge=0.1,
        le=0.75,
    )
    track: list[str] = Field(default=DEFAULT_TRACKED_OBJECTS, title="Objects to track.")
    required_zones: list[str] = Field(
        default_factory=list,
        title="List of required zones to be entered in order to begin autotracking.",
    )
    return_preset: str = Field(
        default="home",
        title="Name of camera preset to return to when object tracking is over.",
    )
    timeout: int = Field(
        default=10, title="Seconds to delay before returning to preset."
    )
    generic_relative: bool = Field(
        default=False,
        title="Allow experimental autotracking with generic ONVIF relative moves.",
    )
    generic_relative_scale: float = Field(
        default=0.15,
        ge=0.01,
        le=1.0,
        title="Scale applied to generic ONVIF relative pan and tilt moves.",
    )
    generic_move_seconds: float = Field(
        default=4.0,
        ge=0.1,
        le=5.0,
        title="Estimated duration of a full-scale generic relative move.",
    )
    movement_weights: Optional[Union[str, list[str]]] = Field(
        default_factory=list,
        title="Internal value used for PTZ movements based on the speed of your camera's motor.",
    )
    enabled_in_config: Optional[bool] = Field(
        default=None, title="Keep track of original state of autotracking."
    )

    @field_validator("movement_weights", mode="before")
    @classmethod
    def validate_weights(cls, v):
        if v is None:
            return None

        if isinstance(v, str):
            weights = list(map(str, map(float, v.split(","))))
        elif isinstance(v, list):
            weights = [str(float(val)) for val in v]
        else:
            raise ValueError("Invalid type for movement_weights")

        if len(weights) != 6:
            raise ValueError(
                "movement_weights must have exactly 6 floats, remove this line from your config and run autotracking calibration"
            )

        return weights


class PtzPatrolStepConfig(FrigateBaseModel):
    preset: str = Field(min_length=1, title="ONVIF preset name.")
    dwell: int = Field(
        default=10,
        ge=1,
        le=3600,
        title="Seconds to remain at this preset before advancing.",
    )


class PtzPatrolConfig(FrigateBaseModel):
    enabled: bool = Field(default=False, title="Start the PTZ patrol automatically.")
    object_tracking: bool = Field(
        default=False,
        title="Pause this patrol while Frigate follows a detected object.",
    )
    steps: list[PtzPatrolStepConfig] = Field(
        default_factory=list,
        max_length=64,
        title="Ordered ONVIF presets and dwell times for the patrol.",
    )

    @model_validator(mode="after")
    def validate_enabled_patrol(self):
        if self.enabled and len(self.steps) < 2:
            raise ValueError("an enabled patrol requires at least two steps")
        return self


class OnvifConfig(FrigateBaseModel):
    host: EnvString = Field(default="", title="Onvif Host")
    port: int = Field(default=8000, title="Onvif Port")
    user: Optional[EnvString] = Field(default=None, title="Onvif Username")
    password: Optional[EnvString] = Field(default=None, title="Onvif Password")
    tls_insecure: bool = Field(default=False, title="Onvif Disable TLS verification")
    autotracking: PtzAutotrackConfig = Field(
        default_factory=PtzAutotrackConfig,
        title="PTZ auto tracking config.",
    )
    patrol: PtzPatrolConfig = Field(
        default_factory=PtzPatrolConfig,
        title="PTZ preset patrol configuration.",
    )
    ignore_time_mismatch: bool = Field(
        default=False,
        title="Onvif Ignore Time Synchronization Mismatch Between Camera and Server",
    )
