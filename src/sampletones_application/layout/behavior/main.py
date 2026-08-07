from pydantic import BaseModel, Field


class MainBehavior(BaseModel, extra="forbid", frozen=True):
    fps_update_interval: float
    vsync: bool
    max_fps: int = Field(ge=0)
