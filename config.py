from pydantic import BaseModel, Field

from constants import MAX_RATE, MIN_RATE


class Config(BaseModel):
    change_rate: float = Field(..., ge=MIN_RATE, le=MAX_RATE)
    sample_rate: int = Field(..., ge=1)
    a4_frequency: float = Field(..., gt=20.0, lt=20000.0)
    a4_pitch: int = Field(..., ge=0, le=127)
    min_pitch: int = Field(..., ge=0, le=127)
    max_pitch: int = Field(..., ge=0, le=127)
    min_fft_size: int = Field(..., ge=256)
    spectral_loss_weight: float = Field(..., ge=0.0, le=1.0)
    temporal_loss_weight: float = Field(..., ge=0.0, le=1.0)
    continuity_loss_weight: float = Field(..., ge=0.0, le=1.0)

    class Config:
        frozen = True

    @property
    def frame_length(self) -> int:
        return round(self.sample_rate / self.change_rate)
