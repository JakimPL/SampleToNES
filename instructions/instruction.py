from typing import Self

from pydantic import BaseModel


class Instruction(BaseModel):
    on: bool

    class Config:
        frozen = True

    def distance(self, other: Self) -> float:
        raise NotImplementedError("Subclasses must implement distance method")
