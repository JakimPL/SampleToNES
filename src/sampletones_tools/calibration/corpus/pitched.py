import math
from functools import partial
from typing import Callable, Final, List, Sequence, Tuple

import numpy as np

from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_tools.calibration.config.pitched import PitchedConfig, VoiceConfig
from sampletones_tools.synthesis.envelopes.exponential_decay import ExponentialDecayEnvelope
from sampletones_tools.synthesis.envelopes.gate import GateEnvelope
from sampletones_tools.synthesis.envelopes.periodic_decay import PeriodicDecayEnvelope
from sampletones_tools.synthesis.envelopes.types import EnvelopeUnion
from sampletones_tools.synthesis.frequency import resolve_frequency
from sampletones_tools.synthesis.oscillators.sine import SineOscillator
from sampletones_tools.synthesis.oscillators.vibrato import CENTS_PER_OCTAVE, VibratoOscillator
from sampletones_tools.synthesis.oscillators.white_noise import WhiteNoiseOscillator
from sampletones_tools.synthesis.voice.layer import Layer
from sampletones_tools.synthesis.voice.voice import Voice

from .families import Family
from .item import CorpusItem, StemsSources
from .truth import PitchLine, Truth

LINE: Final[str] = "line"
BASS_LINE: Final[str] = "bass"
VOICE_LINE: Final[str] = "voice"
FRAME_CENTER: Final[float] = 0.5
DECIBELS_PER_AMPLITUDE_DECADE: Final[float] = 20.0
NYQUIST_SHARE: Final[float] = 0.5
SILENT_SEED: Final[int] = 0

PITCHED_CATALOG: Final[List[Tuple[Family, str]]] = [
    (Family.SINES, "sines-decaying"),
    (Family.SINES, "sines-vibrato"),
    (Family.SINES, "sines-line"),
    (Family.TONES, "tones-line"),
    (Family.TONES, "tones-voice"),
    (Family.TONES, "tones-pluck"),
    (Family.TONES, "tones-vibrato"),
    (Family.COMPOSITES, "composites-band"),
]

FrequencyAt = Callable[[np.ndarray], np.ndarray]


def build_pitched(sample_rate: int, frame_rate: int, *, config: PitchedConfig) -> List[CorpusItem]:
    """Synthesized sounds whose pitch the corpus knows at every moment, each carrying it as a line.

    Sines that decay or swing in pitch, and a bass line, form the ``sines`` family. The same bass
    line as a sawtooth, a vowel-like melody, plucked tones and swinging sawtooths form the ``tones``
    family. The sawtooth bass, the melody and a drum pattern together, each a stem of its own, form
    the ``composites`` family's band. A sound counts as sounding its pitch while its level stays
    within the audible range of its start, so a decay's quiet tail is left out of the reading.

    Args:
        sample_rate: The rate the sounds are synthesized at.
        frame_rate: The frames per second the pitch lines are written at.
        config: The sounds.

    Returns:
        List[CorpusItem]: Every sound, the sines first.
    """
    maker = _Maker(sample_rate, frame_rate, config)
    bass, voice = maker.line(sawtooth=True), maker.voice()
    return [
        *maker.decaying(),
        *maker.vibrato_sines(),
        maker.line(sawtooth=False),
        bass,
        voice,
        *maker.plucks(),
        *maker.vibrato_sawtooths(),
        maker.band(bass, voice),
    ]


class _Maker:
    def __init__(self, sample_rate: int, frame_rate: int, config: PitchedConfig) -> None:
        self._sample_rate = sample_rate
        self._frame_rate = frame_rate
        self._config = config
        self._audible = 10 ** (-config.audible_decibels / DECIBELS_PER_AMPLITUDE_DECADE)

    def decaying(self) -> List[CorpusItem]:
        spec = self._config.decaying
        items: List[CorpusItem] = []
        for frequency in spec.frequencies:
            for constant in spec.time_constants_seconds:
                decay = ExponentialDecayEnvelope(kind="exponential_decay", time_constant_seconds=constant)
                layer = Layer(oscillator=SineOscillator(kind="sine", frequency=frequency), envelopes=(decay,), gain=1.0)
                items.append(
                    self._item(
                        f"sine-decay-{frequency:g}hz-{constant:g}s",
                        Family.SINES,
                        "sines-decaying",
                        [layer],
                        spec.seconds,
                        partial(_steady, frequency),
                        partial(_decaying, constant, self._audible),
                    )
                )
        return items

    def vibrato_sines(self) -> List[CorpusItem]:
        spec = self._config.vibrato
        items: List[CorpusItem] = []
        for frequency in spec.frequencies:
            for depth in spec.depths_cents:
                swinging = self._vibrato(frequency, depth, harmonic=1)
                items.append(
                    self._item(
                        f"sine-vibrato-{frequency:g}hz-{depth:g}c",
                        Family.SINES,
                        "sines-vibrato",
                        [Layer(oscillator=swinging, envelopes=(), gain=1.0)],
                        spec.seconds,
                        swinging.frequency_at,
                        lambda times: np.ones_like(times, dtype=bool),
                    )
                )
        return items

    def vibrato_sawtooths(self) -> List[CorpusItem]:
        spec = self._config.vibrato
        items: List[CorpusItem] = []
        for depth in spec.depths_cents:
            layers = [
                Layer(
                    oscillator=self._vibrato(spec.sawtooth_frequency, depth, harmonic=harmonic),
                    envelopes=(),
                    gain=1.0 / harmonic,
                )
                for harmonic in self._harmonics(
                    spec.sawtooth_frequency * 2 ** (depth / CENTS_PER_OCTAVE), spec.harmonics
                )
            ]
            fundamental = self._vibrato(spec.sawtooth_frequency, depth, harmonic=1)
            items.append(
                self._item(
                    f"saw-vibrato-{depth:g}c",
                    Family.TONES,
                    "tones-vibrato",
                    layers,
                    spec.seconds,
                    fundamental.frequency_at,
                    lambda times: np.ones_like(times, dtype=bool),
                )
            )
        return items

    def line(self, *, sawtooth: bool) -> CorpusItem:
        spec = self._config.line
        layers: List[Layer] = []
        for index, pitch in enumerate(spec.pitches):
            frequency = resolve_frequency(pitch)
            gate = self._gate(index, spec.note_seconds, spec.sounding_share)
            harmonics = self._harmonics(frequency, spec.harmonics) if sawtooth else [1]
            layers.extend(
                Layer(
                    oscillator=SineOscillator(kind="sine", frequency=harmonic * frequency),
                    envelopes=(gate,),
                    gain=1.0 / harmonic,
                )
                for harmonic in harmonics
            )
        frequencies = [resolve_frequency(pitch) for pitch in spec.pitches]
        return self._item(
            "saw-line" if sawtooth else "sine-line",
            Family.TONES if sawtooth else Family.SINES,
            "tones-line" if sawtooth else "sines-line",
            layers,
            spec.note_seconds * len(spec.pitches),
            lambda times: self._note_values(times, frequencies, spec.note_seconds),
            lambda times: self._note_sounding(times, spec.note_seconds, spec.sounding_share, len(frequencies)),
        )

    def voice(self) -> CorpusItem:
        spec = self._config.voice
        layers: List[Layer] = []
        swinging: List[VibratoOscillator] = []
        for index, pitch in enumerate(spec.pitches):
            frequency = resolve_frequency(pitch)
            gate = self._gate(index, spec.note_seconds, spec.sounding_share)
            gains = _formant_gains(frequency, self._harmonics(frequency, spec.harmonics), spec)
            fundamental = VibratoOscillator(
                kind="vibrato",
                frequency=frequency,
                rate_hertz=spec.rate_hertz,
                depth_cents=spec.depth_cents,
                harmonic=1,
            )
            swinging.append(fundamental)
            layers.extend(
                Layer(oscillator=fundamental.model_copy(update={"harmonic": harmonic}), envelopes=(gate,), gain=gain)
                for harmonic, gain in gains
            )

        def frequency_at(times: np.ndarray) -> np.ndarray:
            notes = np.clip((times // spec.note_seconds).astype(int), 0, len(swinging) - 1)
            return np.array([swinging[note].frequency_at(np.array([time]))[0] for note, time in zip(notes, times)])

        return self._item(
            "vowel-melody",
            Family.TONES,
            "tones-voice",
            layers,
            spec.note_seconds * len(spec.pitches),
            frequency_at,
            lambda times: self._note_sounding(times, spec.note_seconds, spec.sounding_share, len(swinging)),
        )

    def plucks(self) -> List[CorpusItem]:
        spec = self._config.pluck
        items: List[CorpusItem] = []
        for frequency in spec.frequencies:
            layers = [
                Layer(
                    oscillator=SineOscillator(kind="sine", frequency=harmonic * frequency),
                    envelopes=(
                        ExponentialDecayEnvelope(
                            kind="exponential_decay", time_constant_seconds=spec.time_constant_seconds / harmonic
                        ),
                    ),
                    gain=1.0 / harmonic,
                )
                for harmonic in self._harmonics(frequency, spec.harmonics)
            ]
            items.append(
                self._item(
                    f"pluck-{frequency:g}hz",
                    Family.TONES,
                    "tones-pluck",
                    layers,
                    spec.seconds,
                    partial(_steady, frequency),
                    partial(_decaying, spec.time_constant_seconds, self._audible),
                )
            )
        return items

    def band(self, bass: CorpusItem, voice: CorpusItem) -> CorpusItem:
        """The sawtooth bass line, the vowel melody and a drum pattern together, each a stem of its own.

        The stems keep the balance their levels set, and are scaled together so their mix peaks at the
        corpus amplitude.
        """
        spec = self._config.band
        length = max(len(bass.audio), len(voice.audio))
        seconds = length / self._sample_rate
        drums = Voice(
            duration_seconds=seconds,
            layers=tuple(
                Layer(
                    oscillator=WhiteNoiseOscillator(kind="white_noise"),
                    envelopes=(
                        PeriodicDecayEnvelope(
                            kind="periodic_decay",
                            period_seconds=hit.period_seconds,
                            time_constant_seconds=hit.decay_seconds,
                            delay_seconds=hit.delay_seconds,
                        ),
                    ),
                    gain=hit.level,
                )
                for hit in spec.hits
            ),
            filters=(),
        )
        beat = drums.render(sample_rate=self._sample_rate, generator=np.random.default_rng(SILENT_SEED))
        parts = [
            _padded(audio * level, length)
            for audio, level in (
                (bass.audio, spec.bass_level),
                (voice.audio, spec.voice_level),
                (beat, spec.drums_level),
            )
        ]
        peak = float(np.max(np.abs(np.sum(parts, axis=0)))) or 1.0
        sources = tuple((self._config.amplitude * part / peak).astype(np.float32) for part in parts)
        frames = math.ceil(seconds * self._frame_rate)
        lines = {name: _padded_line(item, frames) for name, item in ((BASS_LINE, bass), (VOICE_LINE, voice))}
        return CorpusItem(
            name="band",
            family=Family.COMPOSITES,
            category="composites-band",
            listed=True,
            audio=np.sum(sources, axis=0).astype(np.float32),
            truth=Truth(instructions={}, pitches=lines),
            channels=frozenset(ChannelName.items()),
            stems=StemsSources(sources=sources, config=_band_stems()),
        )

    def _vibrato(self, frequency: float, depth: float, *, harmonic: int) -> VibratoOscillator:
        spec = self._config.vibrato
        return VibratoOscillator(
            kind="vibrato", frequency=frequency, rate_hertz=spec.rate_hertz, depth_cents=depth, harmonic=harmonic
        )

    def _harmonics(self, frequency: float, count: int) -> List[int]:
        """The partials up to ``count`` that stay below the Nyquist limit."""
        return [
            harmonic for harmonic in range(1, count + 1) if harmonic * frequency < NYQUIST_SHARE * self._sample_rate
        ]

    def _gate(self, index: int, note_seconds: float, sounding_share: float) -> EnvelopeUnion:
        start = index * note_seconds
        return GateEnvelope(kind="gate", start_seconds=start, end_seconds=start + sounding_share * note_seconds)

    def _note_values(self, times: np.ndarray, frequencies: Sequence[float], note_seconds: float) -> np.ndarray:
        notes = np.clip((times // note_seconds).astype(int), 0, len(frequencies) - 1)
        return np.asarray(np.asarray(frequencies, dtype=np.float64)[notes], dtype=np.float64)

    def _note_sounding(self, times: np.ndarray, note_seconds: float, sounding_share: float, notes: int) -> np.ndarray:
        within = times - (times // note_seconds) * note_seconds
        return (within < sounding_share * note_seconds) & (times < notes * note_seconds)

    def _item(
        self,
        name: str,
        family: Family,
        category: str,
        layers: Sequence[Layer],
        seconds: float,
        frequency_at: FrequencyAt,
        sounding: Callable[[np.ndarray], np.ndarray],
    ) -> CorpusItem:
        voice = Voice(duration_seconds=seconds, layers=tuple(layers), filters=())
        audio = voice.render(sample_rate=self._sample_rate, generator=np.random.default_rng(SILENT_SEED))
        peak = float(np.max(np.abs(audio))) or 1.0
        times = (np.arange(math.ceil(seconds * self._frame_rate)) + FRAME_CENTER) / self._frame_rate
        line: PitchLine = tuple(
            float(frequency) if heard else None for frequency, heard in zip(frequency_at(times), sounding(times))
        )
        return CorpusItem(
            name=name,
            family=family,
            category=category,
            listed=True,
            audio=(self._config.amplitude * audio / peak).astype(np.float32),
            truth=Truth(instructions={}, pitches={LINE: line}),
            channels=None,
            stems=None,
        )


def _padded(audio: np.ndarray, length: int) -> np.ndarray:
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
    """The band's setup: the bass on the triangle, the melody on either pulse, the drums on the noise."""
    parts = ([ChannelName.TRIANGLE], [ChannelName.PULSE1, ChannelName.PULSE2], [ChannelName.NOISE])
    return StemsConfig(
        entries=tuple(
            StemEntry(id=index, settings=StemSettings.covering(channels).model_copy(update={"channel_cap": 1}))
            for index, channels in enumerate(parts)
        ),
        hierarchy=StemsHierarchy(levels=((0, 1, 2),)),
    )


def _steady(frequency: float, times: np.ndarray) -> np.ndarray:
    """The one frequency a steady sound holds, at every time."""
    return np.full_like(times, frequency)


def _decaying(time_constant: float, audible: float, times: np.ndarray) -> np.ndarray:
    """Whether a decay struck at the start still sounds within the audible range at each time."""
    return np.asarray(np.exp(-times / time_constant) >= audible)


def _formant_gains(frequency: float, harmonics: Sequence[int], spec: VoiceConfig) -> List[Tuple[int, float]]:
    """Each harmonic's gain under the formants: a Gaussian bump per formant over a floor, the loudest at one."""
    gains = [
        spec.formant_floor
        + sum(math.exp(-0.5 * ((harmonic * frequency - center) / width) ** 2) for center, width in spec.formants)
        for harmonic in harmonics
    ]
    loudest = max(gains)
    return [(harmonic, gain / loudest) for harmonic, gain in zip(harmonics, gains)]
