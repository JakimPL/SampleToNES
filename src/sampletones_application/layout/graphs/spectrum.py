from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class SpectrumLayout(BaseModel, extra="forbid", frozen=True):
    max_display_bins: int
    color_dim: WrittenColor
    color_bright: WrittenColor
