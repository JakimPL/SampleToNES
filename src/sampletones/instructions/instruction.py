from typing import Self

from pydantic import ConfigDict

from sampletones.constants.enums import InstructionClassName
from sampletones.data import DataModel


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
    def null_instruction(cls) -> Self:
        raise NotImplementedError("Subclasses must implement null_instruction method")

    @classmethod
    def class_name(cls) -> InstructionClassName:
        raise NotImplementedError("Subclasses must implement class_name method")
