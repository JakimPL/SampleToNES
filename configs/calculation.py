from pydantic import BaseModel, Field

from constants import FAST_DIFFERENCE, FIND_BEST_PHASE


class CalculationConfig(BaseModel):
    find_best_phase: bool = Field(default=FIND_BEST_PHASE)
    fast_difference: bool = Field(default=FAST_DIFFERENCE)

    class Config:
        extra = "forbid"
        frozen = True
