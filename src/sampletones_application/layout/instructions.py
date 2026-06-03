from pydantic import BaseModel

RGBA = tuple[int, int, int, int]


class InstructionDimensions(BaseModel, frozen=True):
    instruction_choice_height: int
    instruction_choice_input_width: int


class InstructionValues(BaseModel, frozen=True):
    float_precision: int


class InstructionColors(BaseModel, frozen=True):
    library: RGBA
    generator: RGBA
    group: RGBA
    instruction: RGBA


class InstructionsLayout(BaseModel, frozen=True):
    dimensions: InstructionDimensions
    values: InstructionValues
    colors: InstructionColors
