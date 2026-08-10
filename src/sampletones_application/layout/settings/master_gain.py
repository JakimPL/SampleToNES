from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class MasterGainLayout(BaseModel, extra="forbid", frozen=True):
    slider_width: int
    label_color: WrittenColor
    clip_color: WrittenColor
