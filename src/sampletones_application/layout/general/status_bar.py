from pydantic import BaseModel

from sampletones_application.layout.primitives import Padding


class StatusBarLayout(BaseModel, extra="forbid", frozen=True):
    height: int
    reserved_margin: int
    frame_rounding: int
    frame_padding: Padding
