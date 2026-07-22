from pydantic import BaseModel


class ConverterLayout(BaseModel, extra="forbid", frozen=True):
    width: int
    height: int
    button_height: int
