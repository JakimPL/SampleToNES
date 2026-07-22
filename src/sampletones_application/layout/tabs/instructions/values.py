from pydantic import BaseModel


class InstructionValues(BaseModel, extra="forbid", frozen=True):
    float_precision: int
