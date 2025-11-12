from typing import Self

from pydantic import BaseModel, ConfigDict


class Instruction(BaseModel):
    model_config = ConfigDict(frozen=True)

    on: bool

    @property
    def name(self) -> str:
        raise NotImplementedError("Subclasses must implement name property")

    def distance(self, other: Self) -> float:
        raise NotImplementedError("Subclasses must implement distance method")
