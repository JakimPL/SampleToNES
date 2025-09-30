from pydantic import BaseModel


class Instruction(BaseModel):
    on: bool

    class Config:
        frozen = True

    @staticmethod
    def distance(instruction1: "Instruction", instruction2: "Instruction") -> float:
        raise NotImplementedError("Subclasses must implement distance method")
