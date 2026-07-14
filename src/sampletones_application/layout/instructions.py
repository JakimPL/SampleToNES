from pydantic import BaseModel

from sampletones_application.utils.palette import PaletteColor


class InstructionChoiceLayout(BaseModel, extra="forbid", frozen=True):
    height: int
    input_width: int
    label_width: int


class InstructionValues(BaseModel, extra="forbid", frozen=True):
    float_precision: int


class InstructionColors(BaseModel, extra="forbid", frozen=True):
    library: PaletteColor
    generator: PaletteColor
    group: PaletteColor
    instruction: PaletteColor


class InstructionsLayout(BaseModel, extra="forbid", frozen=True):
    instruction_choice: InstructionChoiceLayout
    values: InstructionValues
    colors: InstructionColors
