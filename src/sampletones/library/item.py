from functools import cached_property
from types import ModuleType
from typing import Generic, Self, cast

from pydantic import ConfigDict, Field

from sampletones.constants.enums import InstructionClassName
from sampletones.data import DataModel
from sampletones.exceptions import InstructionTypeMismatchError
from sampletones.generators import GeneratorType
from sampletones.instructions import (
    INSTRUCTION_CLASS_MAP,
    InstructionData,
    InstructionType,
)

from .fragment import LibraryFragment


class LibraryItem(DataModel, Generic[InstructionType, GeneratorType]):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True, use_enum_values=True)

    instruction_data: InstructionData = Field(..., description="Instruction data")
    fragment: LibraryFragment[InstructionType, GeneratorType] = Field(
        ...,
        description="Library fragment associated with the instruction",
    )

    @classmethod
    def create(
        cls,
        instruction: InstructionType,
        fragment: LibraryFragment[InstructionType, GeneratorType],
    ) -> Self:
        return cls(
            instruction_data=InstructionData.create(instruction),
            fragment=fragment,
        )

    @cached_property
    def instruction_class(self) -> InstructionClassName:
        return self.instruction_data.instruction_class

    @cached_property
    def instruction(self) -> InstructionType:
        if not isinstance(
            self.instruction_data.instruction,
            INSTRUCTION_CLASS_MAP[self.instruction_class],
        ):
            raise InstructionTypeMismatchError("Instruction type does not match the expected class")
        return cast(InstructionType, self.instruction_data.instruction)

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        import schemas.library.FBLibraryItem as FBLibraryItem

        return FBLibraryItem

    @classmethod
    def buffer_reader(cls) -> type:
        import schemas.library.FBLibraryItem as FBLibraryItem

        return FBLibraryItem.FBLibraryItem
