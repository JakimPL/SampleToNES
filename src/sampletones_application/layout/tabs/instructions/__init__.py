from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions
from sampletones_application.layout.tabs.instructions.choice import ChoiceLayout
from sampletones_application.layout.tabs.instructions.values import InstructionValues


class InstructionsLayout(BaseModel, extra="forbid", frozen=True):
    choice: ChoiceLayout
    values: InstructionValues
    right_column: Dimensions
