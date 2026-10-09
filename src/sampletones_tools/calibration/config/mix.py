from typing import Tuple

from pydantic import BaseModel, Field, PositiveFloat


class MixConfig(BaseModel, frozen=True):
    """Tone-plus-noise probes: a steady tone under steady noise, and a bass under hi-hat ticks."""

    noise_levels: Tuple[PositiveFloat, ...] = Field(
        min_length=1,
        description="Noise standard deviations relative to the unit reference tone, one probe each.",
    )
    bass_frequency: PositiveFloat = Field(
        description="Frequency of the sine bass under the hi-hats in Hz.",
    )
    hat_period_seconds: float = Field(
        gt=0.0,
        description="Time between hi-hat ticks in seconds.",
    )
    hat_decay_seconds: float = Field(
        gt=0.0,
        description="Exponential decay constant of every hi-hat tick.",
    )
    hat_level: float = Field(
        gt=0.0,
        description="Scale of the hi-hat noise against the unit-level bass.",
    )
