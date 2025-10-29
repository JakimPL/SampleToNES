from pydantic import BaseModel, Field

from constants.general import (
    CONTINUITY_LOSS_WEIGHT,
    RESET_PHASE,
    SPECTRAL_LOSS_WEIGHT,
    TEMPORAL_LOSS_WEIGHT,
)


class GenerationConfig(BaseModel):
    spectral_loss_weight: float = Field(default=SPECTRAL_LOSS_WEIGHT, ge=0.0, le=1.0)
    temporal_loss_weight: float = Field(default=TEMPORAL_LOSS_WEIGHT, ge=0.0, le=1.0)
    continuity_loss_weight: float = Field(default=CONTINUITY_LOSS_WEIGHT, ge=0.0, le=1.0)
    reset_phase: bool = Field(default=RESET_PHASE)

    class Config:
        extra = "forbid"
        frozen = True
