from abc import ABC, abstractmethod
from typing import Self

from pydantic import ConfigDict

from sampletones.constants.enums import InstructionClassName
from sampletones.data import DataModel


class Instruction(DataModel, ABC):
    model_config = ConfigDict(extra="forbid", frozen=True)

    on: bool

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def distance(self, other: Self) -> float: ...

    @abstractmethod
    def __lt__(self, other: Self) -> bool: ...

    @classmethod
    @abstractmethod
    def null_instruction(cls) -> Self: ...

    @classmethod
    @abstractmethod
    def default_instruction(cls) -> Self: ...

    @classmethod
    @abstractmethod
    def class_name(cls) -> InstructionClassName: ...
