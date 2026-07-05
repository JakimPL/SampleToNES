from __future__ import annotations

from typing import Any, Dict, Generic, Self, Tuple, Type

from pydantic import ConfigDict, Field

from sampletones_core.constants.enums import InstructionClassName
from sampletones_core.data import DataModel
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
    def union_map(cls) -> Dict[int, Type[DataModel]]:
        return {
            index + 1: INSTRUCTION_CLASS_MAP[InstructionClassName(instruction_class)]
            for index, instruction_class in enumerate(InstructionClassName)
        }
