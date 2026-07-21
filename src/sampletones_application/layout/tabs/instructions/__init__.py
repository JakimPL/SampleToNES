from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions
from sampletones_application.layout.tabs.instructions.colors import InstructionColors
from sampletones_application.layout.tabs.instructions.instruction_choice import (
    InstructionChoiceLayout,
)
from sampletones_application.layout.tabs.instructions.values import InstructionValues


class InstructionsLayout(BaseModel, extra="forbid", frozen=True):
    choice: InstructionChoiceLayout
    values: InstructionValues
    colors: InstructionColors
    right_column: Dimensions
