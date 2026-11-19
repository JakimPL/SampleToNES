from typing import List, Self, Tuple

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.calibration.paths import PITCHED_CONFIG_PATH

Frequency = float
Pitch = int


class DecayingConfig(BaseModel):
    """Sines struck once and left to decay."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    frequencies: List[Frequency] = Field(min_length=1)
    time_constants_seconds: List[float] = Field(
        min_length=1, description="How fast each one decays, as time constants."
    )
    seconds: float = Field(gt=0.0)


class VibratoConfig(BaseModel):
    """Tones whose pitch swings: sines at several frequencies, and a sawtooth, at every depth."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    frequencies: List[Frequency] = Field(min_length=1, description="The sines' frequencies.")
    sawtooth_frequency: Frequency
    rate_hertz: float = Field(gt=0.0)
    depths_cents: List[float] = Field(min_length=1)
    harmonics: PositiveInt = Field(description="The partials the sawtooth is built of, those below the Nyquist limit.")
    seconds: float = Field(gt=0.0)


class LineConfig(BaseModel):
    """A bass line of separated notes, played as sines and again as a sawtooth."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pitches: List[Pitch] = Field(min_length=1, description="The notes, as MIDI note numbers.")
    note_seconds: float = Field(gt=0.0)
    sounding_share: float = Field(gt=0.0, le=1.0, description="The share of each note's time it sounds for.")
    harmonics: PositiveInt


class VoiceConfig(BaseModel):
    """A melody on a vowel-like tone: harmonics shaped by formants, its pitch swinging slightly."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pitches: List[Pitch] = Field(min_length=1, description="The notes, as MIDI note numbers.")
    note_seconds: float = Field(gt=0.0)
    sounding_share: float = Field(gt=0.0, le=1.0)
    harmonics: PositiveInt
    formants: List[Tuple[Frequency, float]] = Field(min_length=1, description="Each formant's center and width, in Hz.")
    formant_floor: float = Field(ge=0.0, description="The level every harmonic keeps outside the formants.")
    rate_hertz: float = Field(gt=0.0)
    depth_cents: float = Field(ge=0.0)


class PluckConfig(BaseModel):
    """Plucked tones: harmonic partials, the higher ones dying away faster."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    frequencies: List[Frequency] = Field(min_length=1)
    time_constant_seconds: float = Field(gt=0.0, description="How fast the fundamental decays.")
    harmonics: PositiveInt
    seconds: float = Field(gt=0.0)


class PitchedConfig(BaseModel):
    """Synthesized sounds of a known pitch at every moment, whose conversions are read against that pitch.

    Attributes:
        amplitude: The peak every sound is brought to.
        audible_decibels: How far below its start a decaying sound still counts as sounding its pitch.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    amplitude: float = Field(gt=0.0, le=1.0)
    audible_decibels: float = Field(gt=0.0)
    decaying: DecayingConfig
    vibrato: VibratoConfig
    line: LineConfig
    voice: VoiceConfig
    pluck: PluckConfig

    @classmethod
    def load(cls) -> Self:
        """The pitched sounds the package ships."""
        return load_yaml_model(PITCHED_CONFIG_PATH, cls)
