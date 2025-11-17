from types import ModuleType
from typing import List

from pydantic import ConfigDict, Field

from sampletones.constants.enums import GeneratorName
from sampletones.data import DataModel
from sampletones.instructions import InstructionData


class InstructionsItem(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    generator_name: GeneratorName = Field(..., description="Name of the generator")
    instructions: List[InstructionData] = Field(..., description="List of instruction data for the generator")

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        import schemas.reconstruction.FBInstructionsItem as FBInstructionsItem

        return FBInstructionsItem

    @classmethod
    def buffer_reader(cls) -> type:
        import schemas.reconstruction.FBInstructionsItem as FBInstructionsItem

        return FBInstructionsItem.FBInstructionsItem
