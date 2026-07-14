from pydantic import BaseModel

from sampletones_application.layout.primitives import Padding


class ButtonsLayout(BaseModel, extra="forbid", frozen=True):
    copy_width: int
    search_width: int
    int_width: int
    frame_rounding: int
    frame_padding: Padding
