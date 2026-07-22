from pydantic import BaseModel

from sampletones_application.utils.palette import PaletteColor


class MasterGainLayout(BaseModel, extra="forbid", frozen=True):
    slider_width: int
    label_color: PaletteColor
    clip_color: PaletteColor
