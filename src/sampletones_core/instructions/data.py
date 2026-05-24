from __future__ import annotations

from typing import Any, Dict, Generic, Self, Tuple, Type

from pydantic import ConfigDict, Field

from sampletones_core.constants.enums import InstructionClassName
from sampletones_core.data import (
    DataModel,
    FlatBufferBuilderProtocol,
    FlatBufferReaderProtocol,
    FlatBufferUnionProtocol,
)
from sampletones_shared.types.data import SerializedData

from .maps import INSTRUCTION_CLASS_MAP
from .types import InstructionT


def _instruction_data(data: SerializedData) -> InstructionData[Any]:
    return InstructionData(**data)


class InstructionData(DataModel, Generic[InstructionT]):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    instruction_class: InstructionClassName = Field(..., description="Name of the generator")
    instruction: InstructionT = Field(..., description="Instruction instance")

    def __reduce__(self) -> Tuple[Any, Tuple[SerializedData]]:
        return (_instruction_data, (dict(self),))

    @classmethod
    def create(cls, instruction: InstructionT) -> Self:
        return cls(
            instruction_class=instruction.class_name(),
            instruction=instruction,
        )

    @property
    def instruction_type(self) -> type:
        return INSTRUCTION_CLASS_MAP[self.instruction_class]

    @classmethod
    def buffer_builder(cls) -> FlatBufferBuilderProtocol:
        from sampletones_schemas.instructions import FBInstructionData

        return FBInstructionData

    @classmethod
    def buffer_reader(cls) -> Type[FlatBufferReaderProtocol]:
        from sampletones_schemas.instructions import FBInstructionData

        return FBInstructionData.FBInstructionData

    @classmethod
    def buffer_union_builder(cls) -> FlatBufferUnionProtocol:
        from sampletones_schemas.instructions import FBInstructionUnion

        return FBInstructionUnion

    @classmethod
    def buffer_union_reader(cls) -> Type[FlatBufferUnionProtocol]:
        from sampletones_schemas.instructions import FBInstructionUnion

        return FBInstructionUnion.FBInstructionUnion

    @classmethod
    def buffer_union_map(cls) -> Dict[int, Type[DataModel]]:
        return {
            index + 1: INSTRUCTION_CLASS_MAP[InstructionClassName(instruction_class)]
            for index, instruction_class in enumerate(InstructionClassName)
        }
