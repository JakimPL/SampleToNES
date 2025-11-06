from typing import Self

from pydantic import BaseModel


class Instruction(BaseModel):
    on: bool

    @property
    def name(self) -> str:
        raise NotImplementedError("Subclasses must implement name property")

    def distance(self, other: Self) -> float:
        raise NotImplementedError("Subclasses must implement distance method")

    class Config:
        frozen = True
