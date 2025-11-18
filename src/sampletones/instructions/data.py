from types import ModuleType
from typing import Generic, Self

from flatbuffers.table import Table
from pydantic import ConfigDict, Field

from sampletones.constants.enums import InstructionClassName
from sampletones.data import DataModel
from sampletones.typehints import SerializedData

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
        import schemas.instructions.FBInstructionData as FBInstructionData

        return FBInstructionData

    @classmethod
    def buffer_reader(cls) -> type:
        import schemas.instructions.FBInstructionData as FBInstructionData

        return FBInstructionData.FBInstructionData

    @classmethod
    def _deserialize_union(cls, table: Table, field_values: SerializedData) -> Self:
        instruction_class_name = InstructionClassName(field_values["instruction_class"])
        instruction_class = INSTRUCTION_CLASS_MAP[instruction_class_name]
        return instruction_class._deserialize_from_table(table)
