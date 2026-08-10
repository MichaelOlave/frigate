from pydantic import BaseModel, Field

from frigate.config import PtzPatrolConfig


class PtzPresetBody(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class PtzPatrolBody(PtzPatrolConfig):
    pass
