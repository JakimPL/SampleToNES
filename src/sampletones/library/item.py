from __future__ import annotations

from functools import cached_property
from typing import Any, Generic, Self, Tuple, Type

from pydantic import ConfigDict, Field

from sampletones.constants.enums import InstructionClassName
from sampletones.data import DataModel, FlatBufferBuilderProtocol, FlatBufferReaderProtocol
from sampletones.exceptions import InstructionTypeMismatchError
from sampletones.instructions import INSTRUCTION_CLASS_MAP, InstructionData, InstructionT
from sampletones.typehints import SerializedData

from .fragment import InstructionLibraryFragment


def _library_item(data: SerializedData) -> LibraryItem[Any]:
    return LibraryItem(**data)


class LibraryItem(DataModel, Generic[InstructionT]):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True, use_enum_values=True)

    instruction_data: InstructionData[InstructionT] = Field(..., description="Instruction data")
    fragment: InstructionLibraryFragment[InstructionT] = Field(
        ...,
        description="Library fragment associated with the instruction",
    )

    def __reduce__(self) -> Tuple[Any, Tuple[SerializedData]]:
        return (_library_item, (dict(self),))

    @classmethod
    def create(
        cls,
        instruction: InstructionT,
        fragment: InstructionLibraryFragment[InstructionT],
    ) -> Self:
        return cls(
            instruction_data=InstructionData.create(instruction),
            fragment=fragment,
        )

    @cached_property
    def instruction_class(self) -> InstructionClassName:
        return self.instruction_data.instruction_class

    @cached_property
    def instruction(self) -> InstructionT:
        if not isinstance(
            self.instruction_data.instruction,
            INSTRUCTION_CLASS_MAP[self.instruction_class],
        ):
            raise InstructionTypeMismatchError("Instruction type does not match the expected class")

        instruction: InstructionT = self.instruction_data.instruction
        return instruction

    @classmethod
    def buffer_builder(cls) -> FlatBufferBuilderProtocol:
        from schemas.library import FBInstructionsLibraryItem

        return FBInstructionsLibraryItem

    @classmethod
    def buffer_reader(cls) -> Type[FlatBufferReaderProtocol]:
        from schemas.library import FBInstructionsLibraryItem

        return FBInstructionsLibraryItem.FBInstructionsLibraryItem
