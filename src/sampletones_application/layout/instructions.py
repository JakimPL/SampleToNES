from pydantic import BaseModel

from sampletones_application.utils.color import RGBA


class InstructionDimensions(BaseModel, extra="forbid", frozen=True):
    instruction_choice_height: int
    instruction_choice_input_width: int
    instruction_choice_label_width: int


class InstructionValues(BaseModel, extra="forbid", frozen=True):
    float_precision: int


class InstructionColors(BaseModel, extra="forbid", frozen=True):
    library: RGBA
    generator: RGBA
    group: RGBA
    instruction: RGBA


class InstructionsLayout(BaseModel, extra="forbid", frozen=True):
    dimensions: InstructionDimensions
    values: InstructionValues
    colors: InstructionColors
