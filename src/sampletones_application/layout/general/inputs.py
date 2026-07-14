from pydantic import BaseModel


class InputsLayout(BaseModel, extra="forbid", frozen=True):
    default_width: int
    search_width: int
    label_width: int
