from pydantic import BaseModel

from sampletones_application.utils.palette.color import PaletteColor


class SpectrumLayout(BaseModel, extra="forbid", frozen=True):
    max_display_bins: int
    color_dim: PaletteColor
    color_bright: PaletteColor
