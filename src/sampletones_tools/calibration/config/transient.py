from typing import Tuple

from pydantic import BaseModel, Field, PositiveFloat


class TransientConfig(BaseModel, frozen=True):
    """Percussive probes: a noise burst, a pitch-swept kick, and a plucked tone."""

    snare_decay_seconds: float = Field(
        gt=0.0,
        description="Exponential decay constant of the noise burst.",
    )
    kick_decay_seconds: float = Field(
        gt=0.0,
        description="Exponential decay constant of the kick amplitude and its pitch sweep.",
    )
    kick_sweep_frequencies: Tuple[PositiveFloat, PositiveFloat] = Field(
        description="Start and end frequencies of the kick pitch sweep in Hz.",
    )
    attack_seconds: float = Field(
        gt=0.0,
        description="Linear attack duration of the plucked tone in seconds.",
    )
    attack_tone_decay_seconds: float = Field(
        gt=0.0,
        description="Exponential decay constant of the plucked tone.",
    )
