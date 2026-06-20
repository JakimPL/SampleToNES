from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.audio import (
    DEFAULT_SAMPLE_RATE,
    MAX_SAMPLE_RATE,
    MIN_SAMPLE_RATE,
)
from sampletones_core.constants.general import (
    DEFAULT_NES_FREQUENCY,
    MAX_NES_FREQUENCY,
    MIN_NES_FREQUENCY,
)
from sampletones_shared.constants.project import (
    DEFAULT_SPEED,
    DEFAULT_TEMPO,
    MAX_SPEED,
    MAX_TEMPO,
    MIN_SPEED,
    MIN_TEMPO,
)


class ProjectSettings(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    nes_frequency: int = Field(
        default=DEFAULT_NES_FREQUENCY,
        ge=MIN_NES_FREQUENCY,
        le=MAX_NES_FREQUENCY,
        description="NES engine refresh rate in Hz (NTSC is 60).",
    )
    sample_rate: int = Field(
        default=DEFAULT_SAMPLE_RATE,
        ge=MIN_SAMPLE_RATE,
        le=MAX_SAMPLE_RATE,
        description="Audio engine sample rate in Hz.",
    )
    tempo: int = Field(
        default=DEFAULT_TEMPO,
        ge=MIN_TEMPO,
        le=MAX_TEMPO,
        description="Playback tempo (beats per minute).",
    )
    speed: int = Field(
        default=DEFAULT_SPEED,
        ge=MIN_SPEED,
        le=MAX_SPEED,
        description="Engine ticks per row.",
    )
