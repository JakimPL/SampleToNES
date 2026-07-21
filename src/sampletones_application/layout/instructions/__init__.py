from pydantic import BaseModel

from sampletones_application.layout.instructions.colors import InstructionColors
from sampletones_application.layout.instructions.instruction_choice import (
    InstructionChoiceLayout,
)
from sampletones_application.layout.instructions.values import InstructionValues


class InstructionsLayout(BaseModel, extra="forbid", frozen=True):
    choice: InstructionChoiceLayout
    values: InstructionValues
    colors: InstructionColors
