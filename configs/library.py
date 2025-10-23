from pydantic import BaseModel, Field

from constants import (
    A4_FREQUENCY,
    A4_PITCH,
    CHANGE_RATE,
    MAX_CHANGE_RATE,
    MAX_SAMPLE_RATE,
    MIN_CHANGE_RATE,
    MIN_SAMPLE_RATE,
    SAMPLE_RATE,
    TRANSFORMATION_GAMMA,
)


class LibraryConfig(BaseModel):
    change_rate: int = Field(default=CHANGE_RATE, ge=MIN_CHANGE_RATE, le=MAX_CHANGE_RATE)
    sample_rate: int = Field(default=SAMPLE_RATE, ge=MIN_SAMPLE_RATE, le=MAX_SAMPLE_RATE)
    a4_frequency: float = Field(default=A4_FREQUENCY, gt=20.0, lt=20000.0)
    a4_pitch: int = Field(default=A4_PITCH, ge=1, le=127)
    transformation_gamma: float = Field(default=TRANSFORMATION_GAMMA)

    @property
    def frame_length(self) -> int:
        return round(self.sample_rate / self.change_rate)

    class Config:
        frozen = True
