from pydantic import BaseModel


class PlusMinusButtonsLayout(BaseModel, extra="forbid", frozen=True):
    button_width: int
    button_height: int
    hold_delay: float
