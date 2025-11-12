from typing import List

from pydantic import BaseModel, ConfigDict, Field

from sampletones.constants import GeneratorName
from sampletones.constants.general import (
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
    model_config = ConfigDict(extra="forbid", frozen=True)

    find_best_phase: bool = Field(default=FIND_BEST_PHASE)
    fast_difference: bool = Field(default=FAST_DIFFERENCE)


class WeightsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    spectral_loss_weight: float = Field(default=SPECTRAL_LOSS_WEIGHT, ge=0.0, le=1.0)
    temporal_loss_weight: float = Field(default=TEMPORAL_LOSS_WEIGHT, ge=0.0, le=1.0)
    continuity_loss_weight: float = Field(default=CONTINUITY_LOSS_WEIGHT, ge=0.0, le=1.0)


class GenerationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mixer: float = Field(default=MIXER, ge=0.0, le=MAX_MIXER)
    reset_phase: bool = Field(default=RESET_PHASE)
    generators: List[GeneratorName] = Field(default_factory=lambda: list(GeneratorName))
    calculation: CalculationConfig = Field(default_factory=CalculationConfig)
    weights: WeightsConfig = Field(default_factory=WeightsConfig)
