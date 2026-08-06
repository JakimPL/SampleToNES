from pydantic import BaseModel

from sampletones_application.utils.palette.color import PaletteColor


class CaretLayout(BaseModel, extra="forbid", frozen=True):
    offset: int
    width_padding: int
    fill: PaletteColor
    border: PaletteColor
