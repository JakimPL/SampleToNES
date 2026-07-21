from pydantic import BaseModel


class InstructionChoiceLayout(BaseModel, extra="forbid", frozen=True):
    height: int
    input_width: int
    label_width: int
