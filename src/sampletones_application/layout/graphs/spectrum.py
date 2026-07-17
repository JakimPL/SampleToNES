from pydantic import BaseModel

from sampletones_application.utils.palette import PaletteColor


class SpectrumLayout(BaseModel, extra="forbid", frozen=True):
    max_display_bins: int
    offset_log: float
    color_dim: PaletteColor
    color_bright: PaletteColor
