from typing import Self

from pydantic import ConfigDict

from sampletones.data.model import DataModel


class Instruction(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    on: bool

    @property
    def name(self) -> str:
        raise NotImplementedError("Subclasses must implement name property")

    def distance(self, other: Self) -> float:
        raise NotImplementedError("Subclasses must implement distance method")
