from pydantic import BaseModel

from sampletones_application.utils.color import RGBA


class InstructionDimensions(BaseModel, frozen=True):
    instruction_choice_height: int
    instruction_choice_input_width: int
    instruction_choice_label_width: int


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
