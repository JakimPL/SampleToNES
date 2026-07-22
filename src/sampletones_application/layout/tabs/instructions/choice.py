from pydantic import BaseModel


class ChoiceLayout(BaseModel, extra="forbid", frozen=True):
    height: int
    input_width: int
    label_width: int
