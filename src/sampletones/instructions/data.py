from types import ModuleType

from pydantic import ConfigDict, Field

from sampletones.constants.enums import InstructionClassName
from sampletones.data import DataModel

from .typehints import InstructionUnion


class InstructionData(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    instruction_class: InstructionClassName = Field(..., description="Name of the generator")
    instruction: InstructionUnion = Field(..., description="Instruction instance")

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        import schemas.instructions.FBInstructionData as FBInstructionData

        return FBInstructionData

    @classmethod
    def buffer_reader(cls) -> type:
        import schemas.instructions.FBInstructionData as FBInstructionData

        return FBInstructionData.FBInstructionData
