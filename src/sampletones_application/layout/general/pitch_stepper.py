from pydantic import BaseModel


class PitchStepperLayout(BaseModel, extra="forbid", frozen=True):
    label_width: int
    value_width: int
    button_column_width: int
    commit_delay: int
    commit_priority: int
