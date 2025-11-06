from typing import List

from pydantic import BaseModel, Field

from constants.enums import GeneratorName
from constants.general import (
    CONTINUITY_LOSS_WEIGHT,
    FAST_DIFFERENCE,
    FIND_BEST_PHASE,
    MAX_MIXER,
    MIXER,
    RESET_PHASE,
    SPECTRAL_LOSS_WEIGHT,
    TEMPORAL_LOSS_WEIGHT,
)


class CalculationConfig(BaseModel):
    find_best_phase: bool = Field(default=FIND_BEST_PHASE)
    fast_difference: bool = Field(default=FAST_DIFFERENCE)

    class Config:
        extra = "forbid"
        frozen = True


class WeightsConfig(BaseModel):
    spectral_loss_weight: float = Field(default=SPECTRAL_LOSS_WEIGHT, ge=0.0, le=1.0)
    temporal_loss_weight: float = Field(default=TEMPORAL_LOSS_WEIGHT, ge=0.0, le=1.0)
    continuity_loss_weight: float = Field(default=CONTINUITY_LOSS_WEIGHT, ge=0.0, le=1.0)

    class Config:
        extra = "forbid"
        frozen = True


class GenerationConfig(BaseModel):
    mixer: float = Field(default=MIXER, ge=0.0, le=MAX_MIXER)
    reset_phase: bool = Field(default=RESET_PHASE)
    generators: List[GeneratorName] = Field(default_factory=lambda: list(GeneratorName))
    calculation: CalculationConfig = Field(default_factory=CalculationConfig)
    weights: WeightsConfig = Field(default_factory=WeightsConfig)

    class Config:
        extra = "forbid"
        frozen = True
