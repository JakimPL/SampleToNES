from pydantic import BaseModel, Field

from constants import (
    A4_FREQUENCY,
    A4_PITCH,
    CHANGE_RATE,
    LIBRARY_DIRECTORY,
    MAX_CHANGE_RATE,
    MAX_PITCH,
    MAX_SAMPLE_RATE,
    MAX_WORKERS,
    MIN_CHANGE_RATE,
    MIN_PITCH,
    MIN_SAMPLE_RATE,
    MIXER,
    SAMPLE_RATE,
)


class GeneralConfig(BaseModel):
    change_rate: int = Field(default=CHANGE_RATE, ge=MIN_CHANGE_RATE, le=MAX_CHANGE_RATE)
    sample_rate: int = Field(default=SAMPLE_RATE, ge=MIN_SAMPLE_RATE, le=MAX_SAMPLE_RATE)
    a4_frequency: float = Field(default=A4_FREQUENCY, gt=20.0, lt=20000.0)
    a4_pitch: int = Field(default=A4_PITCH, ge=1, le=127)
    min_pitch: int = Field(default=MIN_PITCH, ge=1, le=127)
    max_pitch: int = Field(default=MAX_PITCH, ge=1, le=127)
    mixer: float = Field(default=MIXER, ge=0.0, le=100.0)
    library_directory: str = Field(default=LIBRARY_DIRECTORY)
    max_workers: int = Field(default=MAX_WORKERS, ge=1)

    @property
    def frame_length(self) -> int:
        return round(self.sample_rate / self.change_rate)

    class Config:
        frozen = True
