from pydantic import BaseModel, Field

from sampletones_shared.display import Resolution


class WindowLayout(BaseModel, extra="forbid", frozen=True):
    width: int
    height: int
    min_width: int
    min_height: int
    position_x: int
    fullscreen: bool
    max_monitor_ratio: float = Field(gt=0.0, le=1.0)
    fallback_monitor: Resolution
