from types import ModuleType
from typing import Self

from flatbuffers.table import Table
from pydantic import ConfigDict

from sampletones.constants.enums import InstructionClassName
from sampletones.data import DataModel
from sampletones.typehints import SerializedData


class Instruction(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    on: bool

    @property
    def name(self) -> str:
        raise NotImplementedError("Subclasses must implement name property")

    def distance(self, other: Self) -> float:
        raise NotImplementedError("Subclasses must implement distance method")

    def __lt__(self, other: Self) -> bool:
        raise NotImplementedError("Subclasses must implement __lt__ method")

    @classmethod
    def class_name(cls) -> InstructionClassName:
        raise NotImplementedError("Subclasses must implement class_name method")

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        import schemas.instructions.FBInstruction as FBInstruction

        return FBInstruction

    @classmethod
    def buffer_reader(cls) -> type:
        import schemas.instructions.FBInstruction as FBInstruction

        return FBInstruction.FBInstruction

    @classmethod
    def _deserialize_union(cls, table: Table, field_values: SerializedData) -> Self:
        pass
