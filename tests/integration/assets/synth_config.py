from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict

from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import load_yaml

DEFAULT_SEED: Final[int] = 1337


class SynthKind(StrEnum):
    """Selects which synthesizer produces an instrument's audio."""

    KICK = "kick"
    LEAD = "lead"
    HIHAT = "hihat"


class ToneConfig(BaseModel):
    """Parameters of a pitch-swept, decaying sine tone (kick, lead).

    The pitch glides from ``pitch_start`` to ``pitch_end``; equal values give a
    steady tone.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    pitch_start: int
    pitch_end: int
    duration: float
    decay: float


class NoiseConfig(BaseModel):
    """Parameters of a high-pass-filtered noise burst (hihat)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    duration: float
    cutoff_hz: float
    decay: float
    highpass_order: int


class SynthConfig(BaseModel):
    """The synthesis parameters for the integration suite's instruments."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    seed: int = DEFAULT_SEED
    kick: ToneConfig
    lead: ToneConfig
    hihat: NoiseConfig


def load_synth_config(path: Pathlike) -> SynthConfig:
    return SynthConfig.model_validate(load_yaml(path))
