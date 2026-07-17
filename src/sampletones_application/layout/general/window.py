from pydantic import BaseModel


class WindowLayout(BaseModel, extra="forbid", frozen=True):
    width: int
    height: int
    position_x: int
    position_y: int
    fullscreen: bool
