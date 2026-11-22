import math
from dataclasses import dataclass
from functools import partial
from typing import Callable, Final, List, Sequence, Tuple

import numpy as np

from sampletones_core.audio.processing import decibels_to_amplitude
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_tools.calibration.config.pitched import HitConfig, PitchedConfig, VoiceConfig
from sampletones_tools.synthesis.envelopes.exponential_decay import ExponentialDecayEnvelope
from sampletones_tools.synthesis.envelopes.gate import GateEnvelope
from sampletones_tools.synthesis.envelopes.periodic_decay import PeriodicDecayEnvelope
from sampletones_tools.synthesis.frequency import resolve_frequency
from sampletones_tools.synthesis.oscillators.sine import SineOscillator
from sampletones_tools.synthesis.oscillators.vibrato import CENTS_PER_OCTAVE, VibratoOscillator
from sampletones_tools.synthesis.oscillators.white_noise import WhiteNoiseOscillator
from sampletones_tools.synthesis.voice.layer import Layer
from sampletones_tools.synthesis.voice.voice import Voice

from .families import Catalog, Family
from .item import CorpusItem, StemsSources
from .stems import mixed, side_by_side, single_line
from .truth import LINE, PitchLine, Truth, frame_middles, frames_covering

BASS_LINE: Final[str] = "bass"
VOICE_LINE: Final[str] = "voice"
BAND_NAME: Final[str] = "band"
NYQUIST_SHARE: Final[float] = 0.5
PITCHED_SEED: Final[int] = 0
SILENT_PEAK: Final[float] = 1.0
UNIT_GAIN: Final[float] = 1.0
FUNDAMENTAL: Final[int] = 1
FIRST_FRAME: Final[int] = 0
GAUSSIAN_EXPONENT: Final[float] = -0.5

SINES_DECAYING_CATEGORY: Final[str] = "sines-decaying"
SINES_VIBRATO_CATEGORY: Final[str] = "sines-vibrato"
SINES_LINE_CATEGORY: Final[str] = "sines-line"
TONES_LINE_CATEGORY: Final[str] = "tones-line"
TONES_VOICE_CATEGORY: Final[str] = "tones-voice"
TONES_PLUCK_CATEGORY: Final[str] = "tones-pluck"
TONES_VIBRATO_CATEGORY: Final[str] = "tones-vibrato"
BAND_CATEGORY: Final[str] = "composites-band"

PITCHED_CATALOG: Final[Catalog] = [
    (Family.SINES, SINES_DECAYING_CATEGORY),
    (Family.SINES, SINES_VIBRATO_CATEGORY),
    (Family.SINES, SINES_LINE_CATEGORY),
    (Family.TONES, TONES_LINE_CATEGORY),
    (Family.TONES, TONES_VOICE_CATEGORY),
    (Family.TONES, TONES_PLUCK_CATEGORY),
    (Family.TONES, TONES_VIBRATO_CATEGORY),
    (Family.COMPOSITES, BAND_CATEGORY),
]

TimeFunction = Callable[[np.ndarray], np.ndarray]


def build_pitched(sample_rate: int, frame_rate: int, *, config: PitchedConfig) -> List[CorpusItem]:
    """Synthesized sounds whose pitch the corpus knows at every moment, each carrying it as a line.

    Sines that decay or swing in pitch, and a bass line, form the ``sines`` family. The same bass
    line as a sawtooth, a vowel-like melody, plucked tones and swinging sawtooths form the ``tones``
    family. The sawtooth bass, the melody and a drum pattern together, each a stem of its own, form
    the ``composites`` family's band.

    Args:
        sample_rate: The rate the sounds are synthesized at.
        frame_rate: The frames per second the pitch lines are written at.
        config: The sounds.

    Returns:
        List[CorpusItem]: Every sound, the sines first.
    """
    sounds = PitchedSounds(sample_rate, frame_rate, config)
    bass, voice = sounds.line(sawtooth=True), sounds.voice()
    return [
        *sounds.decaying(),
        *sounds.vibrato_sines(),
        sounds.line(sawtooth=False),
        bass,
        voice,
        *sounds.plucks(),
        *sounds.vibrato_sawtooths(),
        sounds.band(bass, voice),
    ]


@dataclass(frozen=True)
class PitchedSound:
    """A synthesized sound and the pitch it sounds at every moment.

    Attributes:
        name: The name its files are written under.
        family: The family it belongs to.
        category: The kind of decision it tests.
        layers: The partials it is built of.
        seconds: How long it lasts.
        frequency_at: The frequency in Hz it sounds at each time.
        sounding_at: Whether it counts as sounding its pitch at each time.
    """

    name: str
    family: Family
    category: str
    layers: Tuple[Layer, ...]
    seconds: float
    frequency_at: TimeFunction
    sounding_at: TimeFunction


@dataclass(frozen=True)
class NoteRow:
    """Notes played one after another, each given ``note_seconds`` and sounding the first share of it.

    The rest closing every note keeps each onset clear of the note before it, so a conversion is read
    on notes it can tell apart.

    Attributes:
        note_seconds: The time each note is given.
        sounding_share: The share of its time each note sounds for.
        notes: How many notes the row holds.
    """

    note_seconds: float
    sounding_share: float
    notes: int

    @property
    def seconds(self) -> float:
        """How long the row lasts."""
        return self.note_seconds * self.notes

    def gate(self, index: int) -> GateEnvelope:
        """The gate sounding the note at ``index`` for its share of its time."""
        start = index * self.note_seconds
        return GateEnvelope(
            kind="gate", start_seconds=start, end_seconds=start + self.sounding_share * self.note_seconds
        )

    def note_at(self, times: np.ndarray) -> np.ndarray:
        """The index of the note whose time holds each of ``times``, the end notes reaching past the row."""
        return np.asarray(np.clip((times // self.note_seconds).astype(int), 0, self.notes - 1))

    def sounding_at(self, times: np.ndarray) -> np.ndarray:
        """Whether each of ``times`` falls in the sounding share of its note, within the row."""
        within = times - (times // self.note_seconds) * self.note_seconds
        return (within < self.sounding_share * self.note_seconds) & (times < self.notes * self.note_seconds)


class PitchedSounds:
    """Makes the pitched sounds at one sample rate, each with the pitch line its frames sound.

    A sound renders from a generator seeded with ``PITCHED_SEED``, which the band's drums alone draw
    their noise from, so every sound is alike on every run. A sound is brought to the corpus
    amplitude at its peak. Its truth is one line, read at the middle of every frame it reaches into:
    the frequency it sounds there, or ``None`` where it counts as silent. A decaying sound counts as
    silent once it falls ``audible_decibels`` below its strike, since a fair test of its pitch ends
    where its tail grows quiet. The band, made of two of these sounds and the drums, holds the lines
    of both.
    """

    def __init__(self, sample_rate: int, frame_rate: int, config: PitchedConfig) -> None:
        self._sample_rate = sample_rate
        self._frame_rate = frame_rate
        self._config = config
        self._audible_floor = decibels_to_amplitude(-config.audible_decibels)

    def decaying(self) -> List[CorpusItem]:
        """Sines struck once and left to decay, at every frequency and every time constant."""
        spec = self._config.decaying
        items: List[CorpusItem] = []
        for frequency in spec.frequencies:
            for constant in spec.time_constants_seconds:
                items.append(self._render(self._decaying_sine(frequency, constant, spec.seconds)))

        return items

    def vibrato_sines(self) -> List[CorpusItem]:
        """Sines swinging in pitch, at every frequency and every depth, each sounding throughout."""
        spec = self._config.vibrato
        items: List[CorpusItem] = []
        for frequency in spec.frequencies:
            for depth in spec.depths_cents:
                swinging = _vibrato(frequency, spec.rate_hertz, depth, harmonic=FUNDAMENTAL)
                sound = PitchedSound(
                    name=f"sine-vibrato-{frequency:g}hz-{depth:g}c",
                    family=Family.SINES,
                    category=SINES_VIBRATO_CATEGORY,
                    layers=(Layer(oscillator=swinging, envelopes=(), gain=UNIT_GAIN),),
                    seconds=spec.seconds,
                    frequency_at=swinging.frequency_at,
                    sounding_at=_always_sounding,
                )
                items.append(self._render(sound))

        return items

    def vibrato_sawtooths(self) -> List[CorpusItem]:
        """A sawtooth swinging in pitch at every depth, its line the swinging fundamental.

        Its partials are those below the Nyquist limit at the top of the swing, so every partial
        stays below the limit while the pitch is high.
        """
        spec = self._config.vibrato
        items: List[CorpusItem] = []
        for depth in spec.depths_cents:
            top = _swing_top(spec.sawtooth_frequency, depth)
            layers = tuple(
                Layer(
                    oscillator=_vibrato(spec.sawtooth_frequency, spec.rate_hertz, depth, harmonic=harmonic),
                    envelopes=(),
                    gain=_sawtooth_gain(harmonic),
                )
                for harmonic in self._harmonics(top, spec.harmonics)
            )
            fundamental = _vibrato(spec.sawtooth_frequency, spec.rate_hertz, depth, harmonic=FUNDAMENTAL)
            sound = PitchedSound(
                name=f"saw-vibrato-{depth:g}c",
                family=Family.TONES,
                category=TONES_VIBRATO_CATEGORY,
                layers=layers,
                seconds=spec.seconds,
                frequency_at=fundamental.frequency_at,
                sounding_at=_always_sounding,
            )
            items.append(self._render(sound))

        return items

    def line(self, *, sawtooth: bool) -> CorpusItem:
        """The bass line, as sines or as a sawtooth: a row of separated notes, each sounding its own pitch."""
        spec = self._config.line
        row = NoteRow(note_seconds=spec.note_seconds, sounding_share=spec.sounding_share, notes=len(spec.pitches))
        frequencies = [resolve_frequency(pitch) for pitch in spec.pitches]
        layers: List[Layer] = []
        for index, frequency in enumerate(frequencies):
            gate = row.gate(index)
            harmonics = self._harmonics(frequency, spec.harmonics) if sawtooth else [FUNDAMENTAL]
            layers.extend(
                Layer(
                    oscillator=SineOscillator(kind="sine", frequency=harmonic * frequency),
                    envelopes=(gate,),
                    gain=_sawtooth_gain(harmonic),
                )
                for harmonic in harmonics
            )

        sound = PitchedSound(
            name="saw-line" if sawtooth else "sine-line",
            family=Family.TONES if sawtooth else Family.SINES,
            category=TONES_LINE_CATEGORY if sawtooth else SINES_LINE_CATEGORY,
            layers=tuple(layers),
            seconds=row.seconds,
            frequency_at=partial(_note_frequencies, row, frequencies),
            sounding_at=row.sounding_at,
        )
        return self._render(sound)

    def voice(self) -> CorpusItem:
        """A melody on a vowel-like tone: a row of notes, each swinging slightly about its pitch.

        Each note's harmonics are shaped by the formants and swing together with its fundamental, so
        the line is the fundamental of the note sounding at each moment.
        """
        spec = self._config.voice
        row = NoteRow(note_seconds=spec.note_seconds, sounding_share=spec.sounding_share, notes=len(spec.pitches))
        layers: List[Layer] = []
        swinging: List[VibratoOscillator] = []
        for index, pitch in enumerate(spec.pitches):
            frequency = resolve_frequency(pitch)
            gate = row.gate(index)
            gains = _formant_gains(frequency, self._harmonics(frequency, spec.harmonics), spec)
            fundamental = _vibrato(frequency, spec.rate_hertz, spec.depth_cents, harmonic=FUNDAMENTAL)
            swinging.append(fundamental)
            layers.extend(
                Layer(oscillator=fundamental.model_copy(update={"harmonic": harmonic}), envelopes=(gate,), gain=gain)
                for harmonic, gain in gains
            )

        sound = PitchedSound(
            name="vowel-melody",
            family=Family.TONES,
            category=TONES_VOICE_CATEGORY,
            layers=tuple(layers),
            seconds=row.seconds,
            frequency_at=partial(_swinging_frequencies, row, swinging),
            sounding_at=row.sounding_at,
        )
        return self._render(sound)

    def plucks(self) -> List[CorpusItem]:
        """Plucked tones: harmonic partials, each decaying as many times faster as its number.

        The fundamental decays slowest, so a pluck counts as sounding while the fundamental stays
        within the audible range.
        """
        spec = self._config.pluck
        items: List[CorpusItem] = []
        for frequency in spec.frequencies:
            layers = tuple(
                Layer(
                    oscillator=SineOscillator(kind="sine", frequency=harmonic * frequency),
                    envelopes=(
                        ExponentialDecayEnvelope(
                            kind="exponential_decay", time_constant_seconds=spec.time_constant_seconds / harmonic
                        ),
                    ),
                    gain=_sawtooth_gain(harmonic),
                )
                for harmonic in self._harmonics(frequency, spec.harmonics)
            )
            sound = PitchedSound(
                name=f"pluck-{frequency:g}hz",
                family=Family.TONES,
                category=TONES_PLUCK_CATEGORY,
                layers=layers,
                seconds=spec.seconds,
                frequency_at=partial(_steady, frequency),
                sounding_at=partial(_decaying, spec.time_constant_seconds, self._audible_floor),
            )
            items.append(self._render(sound))

        return items

    def band(self, bass: CorpusItem, voice: CorpusItem) -> CorpusItem:
        """The sawtooth bass line, the vowel melody and a drum pattern together, each a stem of its own.

        The band lasts as long as its longer line, and the shorter is run on in silence. The stems keep
        the balance their levels set, and are scaled together so their mix peaks at the corpus
        amplitude. The truth holds the lines of the two pitched parts, the bass and the melody.
        """
        spec = self._config.band
        length = max(len(bass.audio), len(voice.audio))
        seconds = length / self._sample_rate
        parts = [
            _padded(audio * level, length)
            for audio, level in (
                (bass.audio, spec.bass_level),
                (voice.audio, spec.voice_level),
                (self._drums(seconds), spec.drums_level),
            )
        ]
        peak = _peak(np.sum(parts, axis=0))
        stems = StemsSources(
            sources=tuple(self._brought_to_amplitude(part, peak) for part in parts), config=_band_stems()
        )
        frames = frames_covering(seconds, self._frame_rate)
        lines = {name: _padded_line(item, frames) for name, item in ((BASS_LINE, bass), (VOICE_LINE, voice))}
        return CorpusItem(
            name=BAND_NAME,
            family=Family.COMPOSITES,
            category=BAND_CATEGORY,
            listed=True,
            audio=mixed(stems.sources),
            truth=Truth(instructions={}, pitches=lines),
            channels=stems.channels,
            stems=stems,
        )

    def _decaying_sine(self, frequency: float, constant: float, seconds: float) -> PitchedSound:
        """A sine at ``frequency`` struck at the start and decaying with the time constant ``constant``."""
        decay = ExponentialDecayEnvelope(kind="exponential_decay", time_constant_seconds=constant)
        layer = Layer(oscillator=SineOscillator(kind="sine", frequency=frequency), envelopes=(decay,), gain=UNIT_GAIN)
        return PitchedSound(
            name=f"sine-decay-{frequency:g}hz-{constant:g}s",
            family=Family.SINES,
            category=SINES_DECAYING_CATEGORY,
            layers=(layer,),
            seconds=seconds,
            frequency_at=partial(_steady, frequency),
            sounding_at=partial(_decaying, constant, self._audible_floor),
        )

    def _drums(self, seconds: float) -> np.ndarray:
        """The drum pattern over ``seconds``: every hit's noise, repeating on its beat."""
        drums = Voice(
            duration_seconds=seconds, layers=tuple(_drum_hit(hit) for hit in self._config.band.hits), filters=()
        )
        return drums.render(sample_rate=self._sample_rate, generator=np.random.default_rng(PITCHED_SEED))

    def _render(self, sound: PitchedSound) -> CorpusItem:
        """The sound rendered and brought to the corpus amplitude at its peak, with its line as its truth."""
        voice = Voice(duration_seconds=sound.seconds, layers=sound.layers, filters=())
        audio = voice.render(sample_rate=self._sample_rate, generator=np.random.default_rng(PITCHED_SEED))
        return CorpusItem(
            name=sound.name,
            family=sound.family,
            category=sound.category,
            listed=True,
            audio=self._brought_to_amplitude(audio, _peak(audio)),
            truth=Truth(instructions={}, pitches={LINE: self._line(sound)}),
            channels=None,
            stems=None,
        )

    def _line(self, sound: PitchedSound) -> PitchLine:
        """The frequency the sound sounds at the middle of each frame it reaches into, ``None`` where silent."""
        times = frame_middles(FIRST_FRAME, frames_covering(sound.seconds, self._frame_rate), self._frame_rate)
        return tuple(
            float(frequency) if heard else None
            for frequency, heard in zip(sound.frequency_at(times), sound.sounding_at(times))
        )

    def _brought_to_amplitude(self, audio: np.ndarray, peak: float) -> np.ndarray:
        """``audio`` scaled so that ``peak`` reaches the corpus amplitude."""
        return (self._config.amplitude * audio / peak).astype(np.float32)

    def _harmonics(self, frequency: float, count: int) -> List[int]:
        """The partials of ``frequency`` up to ``count`` below the Nyquist limit, each sounding where it is built."""
        nyquist = NYQUIST_SHARE * self._sample_rate
        return [harmonic for harmonic in range(FUNDAMENTAL, count + 1) if harmonic * frequency < nyquist]


def _vibrato(frequency: float, rate_hertz: float, depth_cents: float, *, harmonic: int) -> VibratoOscillator:
    """The ``harmonic``-th partial of a tone at ``frequency``, swinging ``depth_cents`` each way.

    The pitch swings ``rate_hertz`` times a second.
    """
    return VibratoOscillator(
        kind="vibrato", frequency=frequency, rate_hertz=rate_hertz, depth_cents=depth_cents, harmonic=harmonic
    )


def _swing_top(frequency: float, depth_cents: float) -> float:
    """The highest frequency a tone at ``frequency`` swinging ``depth_cents`` each way reaches."""
    return frequency * 2 ** (depth_cents / CENTS_PER_OCTAVE)


def _sawtooth_gain(harmonic: int) -> float:
    """A sawtooth partial's gain: each partial falls as one over its number, the fundamental at unity."""
    return 1.0 / harmonic


def _drum_hit(hit: HitConfig) -> Layer:
    """A drum hit: noise struck on its beat and decaying before the next."""
    decay = PeriodicDecayEnvelope(
        kind="periodic_decay",
        period_seconds=hit.period_seconds,
        time_constant_seconds=hit.decay_seconds,
        delay_seconds=hit.delay_seconds,
    )
    return Layer(oscillator=WhiteNoiseOscillator(kind="white_noise"), envelopes=(decay,), gain=hit.level)


def _peak(audio: np.ndarray) -> float:
    """The loudest sample of ``audio``, or ``SILENT_PEAK`` for silence, which scaling then leaves silent."""
    return float(np.max(np.abs(audio))) or SILENT_PEAK


def _padded(audio: np.ndarray, length: int) -> np.ndarray:
    """``audio`` run on in silence, or cut, to ``length`` samples."""
    padded = np.zeros(length, dtype=np.float64)
    padded[: len(audio)] = audio[:length]
    return padded


def _padded_line(item: CorpusItem, frames: int) -> PitchLine:
    """The item's pitch line, run on in silence to ``frames`` frames.

    Raises:
        ValueError: If the item carries no pitch line.
    """
    truth = item.truth
    if truth is None:
        raise ValueError(f"{item.name!r} carries no pitch line")

    line = truth.pitches[LINE]
    return tuple([*line[:frames], *([None] * (frames - len(line)))])


def _band_stems() -> StemsConfig:
    """The band's setup: the bass on the triangle, the melody on either pulse, the drums on the noise.

    Each part is one line, so each stem sounds one of its channels at a time.
    """
    return side_by_side(
        [
            single_line([ChannelName.TRIANGLE]),
            single_line([ChannelName.PULSE1, ChannelName.PULSE2]),
            single_line([ChannelName.NOISE]),
        ]
    )


def _steady(frequency: float, times: np.ndarray) -> np.ndarray:
    """The one frequency a steady sound holds, at every time."""
    return np.full_like(times, frequency)


def _always_sounding(times: np.ndarray) -> np.ndarray:
    """A sound sounding its pitch at every time."""
    return np.ones_like(times, dtype=bool)


def _decaying(time_constant: float, audible_floor: float, times: np.ndarray) -> np.ndarray:
    """Whether a decay struck at the start still stands above ``audible_floor`` of its strike at each time."""
    return np.asarray(np.exp(-times / time_constant) >= audible_floor)


def _note_frequencies(row: NoteRow, frequencies: Sequence[float], times: np.ndarray) -> np.ndarray:
    """The frequency of the note of ``row`` whose time holds each of ``times``."""
    return np.asarray(np.asarray(frequencies, dtype=np.float64)[row.note_at(times)], dtype=np.float64)


def _swinging_frequencies(row: NoteRow, swinging: Sequence[VibratoOscillator], times: np.ndarray) -> np.ndarray:
    """The frequency the swinging fundamental of the note of ``row`` holding each of ``times`` reaches then."""
    notes = row.note_at(times)
    return np.array([swinging[note].frequency_at(np.array([time]))[0] for note, time in zip(notes, times)])


def _formant_gains(frequency: float, harmonics: Sequence[int], spec: VoiceConfig) -> List[Tuple[int, float]]:
    """Each harmonic's gain under the formants: a Gaussian bump per formant over a floor, the loudest at one."""
    gains = [
        spec.formant_floor
        + sum(
            math.exp(GAUSSIAN_EXPONENT * ((harmonic * frequency - center) / width) ** 2)
            for center, width in spec.formants
        )
        for harmonic in harmonics
    ]
    loudest = max(gains)
    return [(harmonic, gain / loudest) for harmonic, gain in zip(harmonics, gains)]
