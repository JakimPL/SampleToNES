from typing import Tuple

from pydantic import BaseModel, Field, PositiveFloat


class PolyphonyConfig(BaseModel, frozen=True):
    """Probes holding more than one voice: a held chord, and a pulse melody over a snare."""

    chord_frequencies: Tuple[PositiveFloat, ...] = Field(
        min_length=2,
        description="Sine frequencies in Hz held together, sharing the unit level equally.",
    )
    melody_frequencies: Tuple[PositiveFloat, ...] = Field(
        min_length=1,
        description="Pulse-wave note frequencies in Hz, played one after another.",
    )
    note_seconds: float = Field(
        gt=0.0,
        description="Duration of every melody note in seconds.",
    )
    note_decay_seconds: float = Field(
        gt=0.0,
        description="Exponential decay constant of every melody note, struck again on each note.",
    )
    snare_period_seconds: float = Field(
        gt=0.0,
        description="Time between snare hits in seconds.",
    )
    snare_delay_seconds: float = Field(
        ge=0.0,
        description="When the first snare hit falls, in seconds.",
    )
    snare_decay_seconds: float = Field(
        gt=0.0,
        description="Exponential decay constant of every snare hit.",
    )
    snare_level: float = Field(
        gt=0.0,
        description="Scale of the snare noise against the unit-level melody.",
    )
