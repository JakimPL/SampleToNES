from pydantic import BaseModel


class PitchStepperLayout(BaseModel, extra="forbid", frozen=True):
    label_width: int
    value_width: int
    button_column_width: int
    button_width: int
    hold_delay: float
    commit_delay: int
    commit_priority: int
