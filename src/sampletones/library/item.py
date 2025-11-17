from types import ModuleType
from typing import Generic, Self

from flatbuffers.table import Table
from pydantic import ConfigDict, Field

from sampletones.constants.enums import InstructionClassName
from sampletones.data import DataModel
from sampletones.generators import (
    GeneratorType,
)
from sampletones.instructions import (
    INSTRUCTION_CLASS_MAP,
    InstructionType,
)
from sampletones.typehints import SerializedData

from .fragment import LibraryFragment


class LibraryItem(DataModel, Generic[InstructionType, GeneratorType]):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True, use_enum_values=True)

    instruction_class: InstructionClassName = Field(..., description="Class name of the instruction")
    instruction: InstructionType = Field(..., description="Instruction instance")
    fragment: LibraryFragment[InstructionType, GeneratorType] = Field(
        ...,
        description="Library fragment associated with the instruction",
    )

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        import schemas.library.FBLibraryItem as FBLibraryItem

        return FBLibraryItem

    @classmethod
    def buffer_reader(cls) -> type:
        import schemas.library.FBLibraryItem as FBLibraryItem

        return FBLibraryItem.FBLibraryItem

    @classmethod
    def _deserialize_union(cls, table: Table, field_values: SerializedData) -> Self:
        instruction_class = InstructionClassName(field_values["instruction_class"])
        instruction_class = INSTRUCTION_CLASS_MAP[instruction_class]
        return instruction_class._deserialize_from_table(table)
