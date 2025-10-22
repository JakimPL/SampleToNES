from pydantic import BaseModel, Field

from constants import (
    A4_FREQUENCY,
    A4_PITCH,
    CHANGE_RATE,
    CONTINUITY_LOSS_WEIGHT,
    FAST_LOG_ARFFT,
    FIND_BEST_PHASE,
    LIBRARY_PATH,
    MAX_CHANGE_RATE,
    MAX_PITCH,
    MAX_SAMPLE_RATE,
    MAX_WORKERS,
    MIN_CHANGE_RATE,
    MIN_PITCH,
    MIN_SAMPLE_RATE,
    MIXER,
    RESET_PHASE,
    SAMPLE_RATE,
    SPECTRAL_LOSS_WEIGHT,
    TEMPORAL_LOSS_WEIGHT,
)


class Config(BaseModel):
    change_rate: int = Field(default=CHANGE_RATE, ge=MIN_CHANGE_RATE, le=MAX_CHANGE_RATE)
    sample_rate: int = Field(default=SAMPLE_RATE, ge=MIN_SAMPLE_RATE, le=MAX_SAMPLE_RATE)
    a4_frequency: float = Field(default=A4_FREQUENCY, gt=20.0, lt=20000.0)
    a4_pitch: int = Field(default=A4_PITCH, ge=1, le=127)
    min_pitch: int = Field(default=MIN_PITCH, ge=1, le=127)
    max_pitch: int = Field(default=MAX_PITCH, ge=1, le=127)
    mixer: float = Field(default=MIXER, ge=0.0, le=100.0)
    spectral_loss_weight: float = Field(default=SPECTRAL_LOSS_WEIGHT, ge=0.0, le=1.0)
    temporal_loss_weight: float = Field(default=TEMPORAL_LOSS_WEIGHT, ge=0.0, le=1.0)
    continuity_loss_weight: float = Field(default=CONTINUITY_LOSS_WEIGHT, ge=0.0, le=1.0)
    reset_phase: bool = Field(default=RESET_PHASE)
    library_path: str = Field(default=LIBRARY_PATH)
    max_workers: int = Field(default=MAX_WORKERS, ge=1)
    find_best_phase: bool = Field(default=FIND_BEST_PHASE)
    fast_log_arfft: bool = Field(default=FAST_LOG_ARFFT)

    class Config:
        frozen = True

    @property
    def frame_length(self) -> int:
        return round(self.sample_rate / self.change_rate)
