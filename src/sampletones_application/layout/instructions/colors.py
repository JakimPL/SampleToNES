from pydantic import BaseModel

from sampletones_application.utils.palette import PaletteColor


class InstructionColors(BaseModel, extra="forbid", frozen=True):
    library: PaletteColor
    generator: PaletteColor
    group: PaletteColor
    instruction: PaletteColor
