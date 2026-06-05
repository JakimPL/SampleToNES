from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.audio import (
    DEFAULT_SAMPLE_RATE,
    MAX_SAMPLE_RATE,
    MIN_SAMPLE_RATE,
)
from sampletones_core.constants.general import (
    DEFAULT_CHANGE_RATE,
    MAX_CHANGE_RATE,
    MIN_CHANGE_RATE,
)
from sampletones_shared.constants.project import (
    DEFAULT_ROWS_PER_PATTERN,
    DEFAULT_SPEED,
    DEFAULT_TEMPO,
    MAX_ROWS_PER_PATTERN,
    MAX_SPEED,
    MAX_TEMPO,
    MIN_ROWS_PER_PATTERN,
    MIN_SPEED,
    MIN_TEMPO,
)


class ProjectSettings(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    change_rate: int = Field(
        default=DEFAULT_CHANGE_RATE,
        ge=MIN_CHANGE_RATE,
        le=MAX_CHANGE_RATE,
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
    rows_per_pattern: int = Field(
        default=DEFAULT_ROWS_PER_PATTERN,
        ge=MIN_ROWS_PER_PATTERN,
        le=MAX_ROWS_PER_PATTERN,
        description="Default number of rows for a newly created pattern.",
    )
