from pydantic import BaseModel


class WindowLayout(BaseModel, extra="forbid", frozen=True):
    width: int
    height: int
    min_width: int
    min_height: int
    position_x: int
    fullscreen: bool
