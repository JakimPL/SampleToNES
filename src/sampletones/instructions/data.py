from types import ModuleType
from typing import Dict, Generic, Self

from pydantic import ConfigDict, Field

from sampletones.constants.enums import InstructionClassName
from sampletones.data import DataModel

from .maps import INSTRUCTION_CLASS_MAP
from .typehints import InstructionType


class InstructionData(DataModel, Generic[InstructionType]):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    instruction_class: InstructionClassName = Field(..., description="Name of the generator")
    instruction: InstructionType = Field(..., description="Instruction instance")

    @classmethod
    def create(
        cls,
        instruction: InstructionType,
    ) -> Self:
        return cls(
            instruction_class=instruction.class_name(),
            instruction=instruction,
        )

    @property
    def instruction_type(self) -> type:
        return INSTRUCTION_CLASS_MAP[self.instruction_class]

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        from schemas.instructions import FBInstructionData

        return FBInstructionData

    @classmethod
    def buffer_reader(cls) -> type:
        from schemas.instructions import FBInstructionData

        return FBInstructionData.FBInstructionData

    @classmethod
    def buffer_union_builder(cls) -> ModuleType:
        from schemas.instructions import FBInstructionUnion

        return FBInstructionUnion

    @classmethod
    def buffer_union_reader(cls) -> type:
        from schemas.instructions import FBInstructionUnion

        return FBInstructionUnion.FBInstructionUnion

    @classmethod
    def buffer_union_map(cls) -> Dict[int, type]:
        return {
            index + 1: INSTRUCTION_CLASS_MAP[instruction_class]
            for index, instruction_class in enumerate(InstructionClassName)
        }
