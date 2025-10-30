from typing import List

from pydantic import BaseModel, Field

from constants.general import (
    CONTINUITY_LOSS_WEIGHT,
    MIXER,
    RESET_PHASE,
    SPECTRAL_LOSS_WEIGHT,
    TEMPORAL_LOSS_WEIGHT,
)
from typehints.general import GENERATOR_NAMES, GeneratorName


class GenerationConfig(BaseModel):
    mixer: float = Field(default=MIXER, ge=0.0, le=100.0)
    spectral_loss_weight: float = Field(default=SPECTRAL_LOSS_WEIGHT, ge=0.0, le=1.0)
    temporal_loss_weight: float = Field(default=TEMPORAL_LOSS_WEIGHT, ge=0.0, le=1.0)
    continuity_loss_weight: float = Field(default=CONTINUITY_LOSS_WEIGHT, ge=0.0, le=1.0)
    reset_phase: bool = Field(default=RESET_PHASE)
    generators: List[GeneratorName] = Field(default_factory=lambda: GENERATOR_NAMES.copy())

    class Config:
        extra = "forbid"
        frozen = True
