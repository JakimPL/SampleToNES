from pydantic import BaseModel, Field

from constants import DEFAULT_TRANSFORMATION_NAME, FAST_LOG_ARFFT, FIND_BEST_PHASE
from typehints.general import TransformationName


class CalculationConfig(BaseModel):
    transformation: TransformationName = Field(default=DEFAULT_TRANSFORMATION_NAME)
    find_best_phase: bool = Field(default=FIND_BEST_PHASE)
    fast_log_arfft: bool = Field(default=FAST_LOG_ARFFT)

    class Config:
        frozen = True
