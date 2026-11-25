from typing import List, Self, Tuple

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.calibration.paths import PITCHED_CONFIG_PATH

Frequency = float
Pitch = int


class DecayingConfig(BaseModel):
    """Sines struck once and left to decay.

    Attributes:
        frequencies: The sines' frequencies.
        time_constants_seconds: How fast each one decays, as time constants.
        seconds: How long each sound lasts.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    frequencies: List[Frequency] = Field(min_length=1)
    time_constants_seconds: List[float] = Field(
        min_length=1, description="How fast each one decays, as time constants."
    )
    seconds: float = Field(gt=0.0)


class VibratoConfig(BaseModel):
    """Tones whose pitch swings: sines at several frequencies, and a sawtooth, at every depth.

    Attributes:
        frequencies: The sines' frequencies.
        sawtooth_frequency: The sawtooth's frequency.
        rate_hertz: How many times a second the pitch swings.
        depths_cents: How far the pitch swings each way, one sound per depth.
        harmonics: The partials the sawtooth is built of, those below the Nyquist limit.
        seconds: How long each sound lasts.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    frequencies: List[Frequency] = Field(min_length=1, description="The sines' frequencies.")
    sawtooth_frequency: Frequency
    rate_hertz: float = Field(gt=0.0)
    depths_cents: List[float] = Field(min_length=1)
    harmonics: PositiveInt = Field(description="The partials the sawtooth is built of, those below the Nyquist limit.")
    seconds: float = Field(gt=0.0)


class LineConfig(BaseModel):
    """A bass line of separated notes, played as sines and again as a sawtooth.

    Attributes:
        pitches: The notes, as MIDI note numbers.
        note_seconds: The time each note is given.
        sounding_share: The share of each note's time it sounds for.
        harmonics: The partials the sawtooth is built of, those below the Nyquist limit.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    pitches: List[Pitch] = Field(min_length=1, description="The notes, as MIDI note numbers.")
    note_seconds: float = Field(gt=0.0)
    sounding_share: float = Field(gt=0.0, le=1.0, description="The share of each note's time it sounds for.")
    harmonics: PositiveInt


class VoiceConfig(BaseModel):
    """A melody on a vowel-like tone: harmonics shaped by formants, its pitch swinging slightly.

    Attributes:
        pitches: The notes, as MIDI note numbers.
        note_seconds: The time each note is given.
        sounding_share: The share of each note's time it sounds for.
        harmonics: The partials each note is built of, those below the Nyquist limit.
        formants: Each formant's center and width, in Hz.
        formant_floor: The level every harmonic keeps outside the formants.
        rate_hertz: How many times a second the pitch swings.
        depth_cents: How far the pitch swings each way.
    """

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
    """Plucked tones: harmonic partials, the higher ones dying away faster.

    Attributes:
        frequencies: The tones' frequencies.
        time_constant_seconds: How fast the fundamental decays.
        harmonics: The partials each tone is built of, those below the Nyquist limit.
        seconds: How long each sound lasts.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    frequencies: List[Frequency] = Field(min_length=1)
    time_constant_seconds: float = Field(gt=0.0, description="How fast the fundamental decays.")
    harmonics: PositiveInt
    seconds: float = Field(gt=0.0)


class HitConfig(BaseModel):
    """A drum hit of noise repeating on a beat.

    Attributes:
        period_seconds: The time between two strikes.
        decay_seconds: How fast each strike decays, as a time constant.
        delay_seconds: When the first strike falls.
        level: The hit's level within the drums.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    period_seconds: float = Field(gt=0.0)
    decay_seconds: float = Field(gt=0.0)
    delay_seconds: float = Field(ge=0.0)
    level: float = Field(gt=0.0)


class BandConfig(BaseModel):
    """The bass line, the melody and a drum pattern together, each a stem of its own.

    Attributes:
        bass_level: The bass line's level in the band.
        voice_level: The melody's level in the band.
        drums_level: The drums' level in the band.
        hits: The drum hits.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    bass_level: float = Field(gt=0.0)
    voice_level: float = Field(gt=0.0)
    drums_level: float = Field(gt=0.0)
    hits: List[HitConfig] = Field(min_length=1)


class PitchedConfig(BaseModel):
    """Synthesized sounds of a known pitch at every moment, whose conversions are read against that pitch.

    Attributes:
        amplitude: The peak every sound is brought to.
        decaying: The decaying sines.
        vibrato: The swinging sines and sawtooths.
        line: The bass line.
        voice: The vowel melody.
        pluck: The plucked tones.
        band: The band of bass, melody and drums.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    amplitude: float = Field(gt=0.0, le=1.0)
    decaying: DecayingConfig
    vibrato: VibratoConfig
    line: LineConfig
    voice: VoiceConfig
    pluck: PluckConfig
    band: BandConfig

    @classmethod
    def load(cls) -> Self:
        """The pitched sounds the package ships."""
        return load_yaml_model(PITCHED_CONFIG_PATH, cls)
