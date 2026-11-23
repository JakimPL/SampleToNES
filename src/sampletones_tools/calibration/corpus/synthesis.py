from dataclasses import dataclass
from functools import partial
from typing import Callable, Dict, Final, List, Optional, Sequence, Tuple

import numpy as np

from sampletones_core.audio.processing import clip_audio
from sampletones_tools.calibration.config.corpus import CorpusConfig
from sampletones_tools.calibration.config.truth import TruthConfig
from sampletones_tools.synthesis.envelopes.exponential_decay import (
    ExponentialDecayEnvelope,
)
from sampletones_tools.synthesis.envelopes.gate import GateEnvelope
from sampletones_tools.synthesis.envelopes.linear_attack import LinearAttackEnvelope
from sampletones_tools.synthesis.envelopes.linear_ramp import LinearRampEnvelope
from sampletones_tools.synthesis.envelopes.periodic_decay import PeriodicDecayEnvelope
from sampletones_tools.synthesis.envelopes.types import EnvelopeUnion
from sampletones_tools.synthesis.oscillators.exponential_glide import (
    ExponentialGlideOscillator,
)
from sampletones_tools.synthesis.oscillators.pulse import PulseOscillator
from sampletones_tools.synthesis.oscillators.sine import SineOscillator
from sampletones_tools.synthesis.oscillators.types import OscillatorUnion
from sampletones_tools.synthesis.oscillators.walk_noise import WalkNoiseOscillator
from sampletones_tools.synthesis.oscillators.white_noise import WhiteNoiseOscillator
from sampletones_tools.synthesis.voice.layer import Layer
from sampletones_tools.synthesis.voice.voice import Voice

from .families import Family
from .item import CorpusItem
from .truth import LINE, TimeFunction, Truth, audible, frames_reached, pitch_line, steady

TONE_CATEGORY: Final[str] = "tone"
TIMBRE_CATEGORY: Final[str] = "timbre"
NOISE_CATEGORY: Final[str] = "noise"
TRANSIENT_CATEGORY: Final[str] = "transient"
DYNAMICS_CATEGORY: Final[str] = "dynamics"
MIX_CATEGORY: Final[str] = "mix"
POLYPHONY_CATEGORY: Final[str] = "polyphony"

PROBE_FAMILIES: Final[Dict[str, Family]] = {
    TONE_CATEGORY: Family.SINES,
    TIMBRE_CATEGORY: Family.TONES,
    NOISE_CATEGORY: Family.TONES,
    TRANSIENT_CATEGORY: Family.TONES,
    DYNAMICS_CATEGORY: Family.TONES,
    MIX_CATEGORY: Family.COMPOSITES,
    POLYPHONY_CATEGORY: Family.COMPOSITES,
}

UNIT_GAIN: Final[float] = 1.0
SQUARE_DUTY_CYCLE: Final[float] = 0.5
FIRST_STRIKE_SECONDS: Final[float] = 0.0


@dataclass(frozen=True)
class ProbePitch:
    """The one pitch a probe's tone holds, and the tone's level over time.

    The level says where the tone counts as sounding its pitch: a tone holds its pitch wherever it
    stands within the audible range of its full level, so a decay's quiet tail and a crescendo's quiet
    start hold none (see ``audible``).

    Attributes:
        frequency: The pitch in Hz.
        level_at: The tone's level at each time, against its full level.
    """

    frequency: float
    level_at: TimeFunction


@dataclass(frozen=True)
class Probe:
    """A probe of the corpus: its name and category, the voice it renders, and the pitch it holds.

    Attributes:
        name: The name its files are written under.
        category: The kind of decision it tests.
        voice: What it renders.
        pitch: The one pitch a tone of the probe holds, or ``None`` for a probe holding no single pitch.
    """

    name: str
    category: str
    voice: Voice
    pitch: Optional[ProbePitch]

    @property
    def family(self) -> Family:
        """The family the probe's category belongs to."""
        return PROBE_FAMILIES[self.category]


@dataclass(frozen=True)
class RenderedProbe:
    """A probe as the corpus pass renders it, each of its layers' audio kept at unit scale.

    Every sound made of a probe comes from this one render, so the probe heard as one recording and
    its parts held as stems hold the same draw of noise.

    Attributes:
        probe: The probe.
        layers: Each layer's audio at unit scale, in the voice's layer order.
        sample_rate: The rate it is rendered at.
    """

    probe: Probe
    layers: Tuple[np.ndarray, ...]
    sample_rate: int

    @property
    def samples(self) -> int:
        """How many samples the render spans, which every layer spans alike over the voice's one time axis."""
        return len(self.layers[0])

    @property
    def audio(self) -> np.ndarray:
        """The probe's audio at unit scale: every layer, mixed as its voice mixes them."""
        return self.probe.voice.mix_layers(self.layers, sample_rate=self.sample_rate)

    def part(self, holds: Callable[[Layer], bool]) -> np.ndarray:
        """The audio at unit scale of the layers ``holds`` picks, mixed as the voice mixes them."""
        picked = [audio for layer, audio in zip(self.probe.voice.layers, self.layers) if holds(layer)]
        return self.probe.voice.mix_layers(picked, sample_rate=self.sample_rate)


def build_corpus(
    sample_rate: int,
    frame_rate: int,
    *,
    config: CorpusConfig,
    truth: TruthConfig,
) -> List[CorpusItem]:
    """
    Synthesize the calibration probe corpus.

    The corpus spans the signal classes the criterion must arbitrate between:
    steady tones across the pitch range, pulse timbres of several duty cycles,
    broadband noise, tone-plus-noise mixes, percussive transients, level changes
    (a crescendo and a burst dropping to a hiss), and voices sounding together.
    Probes render in one pass (see ``render_probes``), so every item is
    deterministic for a fixed sample rate and configuration and referee scores
    are reproducible across runs. A probe whose tone holds one known pitch
    carries it as its truth, one line over every frame its audio reaches: the
    sine tones, the pulse waves, the tones under hiss and under hi-hats, the
    plucked tone and the crescendo. The line is silent where the tone falls
    below the audible range. The other probes' truth is ``None``.

    Args:
        sample_rate: Sampling rate of the synthesized items in Hz.
        frame_rate: The frames per second a pitch line is written at.
        config: Corpus tuning holding the probe parameters per signal class.
        truth: How a probe's pitch line counts its tone as sounding.

    Returns:
        The corpus items, each carrying its category for per-class reporting.
    """
    return [_item(rendered, frame_rate, config, truth) for rendered in render_probes(sample_rate, config)]


def render_probes(sample_rate: int, config: CorpusConfig) -> List[RenderedProbe]:
    """Every probe rendered in one pass, in corpus order, from one generator seeded with the corpus seed.

    The probes draw their noise from the generator in turn, so each probe holds the same draw on
    every run, and every sound made of a probe holds that one draw.

    Args:
        sample_rate: The rate the probes are rendered at.
        config: The probe corpus.

    Returns:
        List[RenderedProbe]: Each probe beside its rendered layers, in corpus order.
    """
    generator = np.random.default_rng(config.seed)
    return [
        RenderedProbe(
            probe=probe,
            layers=tuple(probe.voice.render_layers(sample_rate=sample_rate, generator=generator)),
            sample_rate=sample_rate,
        )
        for probe in corpus_probes(config)
    ]


def at_corpus_level(audio: np.ndarray, config: CorpusConfig) -> np.ndarray:
    """``audio`` at unit scale brought to the corpus level: scaled by the corpus amplitude."""
    return config.amplitude * audio


def corpus_probes(config: CorpusConfig) -> List[Probe]:
    """The probes of the corpus, in the order they render from the corpus generator."""
    return [
        *_tone_probes(config),
        *_timbre_probes(config),
        *_noise_probes(config),
        *_mix_probes(config),
        *_transient_probes(config),
        _crescendo_probe(config),
        *_polyphony_probes(config),
        _burst_then_hiss_probe(config),
        _bass_hi_hats_probe(config),
    ]


def _tone_probes(config: CorpusConfig) -> List[Probe]:
    return [
        Probe(
            name=f"tone-{frequency:g}hz",
            category=TONE_CATEGORY,
            voice=_voice(
                config,
                _layer(
                    SineOscillator(
                        kind="sine",
                        frequency=frequency,
                    )
                ),
            ),
            pitch=_steady_pitch(frequency),
        )
        for frequency in config.tone.frequencies
    ]


def _timbre_probes(config: CorpusConfig) -> List[Probe]:
    return [
        Probe(
            name=f"pulse-duty{duty_cycle:g}",
            category=TIMBRE_CATEGORY,
            voice=_voice(
                config,
                _layer(
                    PulseOscillator(
                        kind="pulse",
                        frequency=config.timbre.frequency,
                        duty_cycle=duty_cycle,
                    )
                ),
            ),
            pitch=_steady_pitch(config.timbre.frequency),
        )
        for duty_cycle in config.timbre.duty_cycles
    ]


def _noise_probes(config: CorpusConfig) -> List[Probe]:
    return [
        _unpitched(
            "noise-white",
            NOISE_CATEGORY,
            _voice(
                config,
                _layer(
                    WhiteNoiseOscillator(kind="white_noise"),
                    gain=config.noise.white_level,
                ),
            ),
        ),
        _unpitched(
            "noise-dark",
            NOISE_CATEGORY,
            _voice(
                config,
                _layer(
                    WalkNoiseOscillator(
                        kind="walk_noise",
                    )
                ),
            ),
        ),
    ]


def _mix_probes(config: CorpusConfig) -> List[Probe]:
    return [
        Probe(
            name=f"mix-noise{noise_level:g}",
            category=MIX_CATEGORY,
            voice=_voice(
                config,
                _layer(
                    SineOscillator(
                        kind="sine",
                        frequency=config.reference_frequency,
                    )
                ),
                _layer(
                    WhiteNoiseOscillator(kind="white_noise"),
                    gain=noise_level,
                ),
            ),
            pitch=_steady_pitch(config.reference_frequency),
        )
        for noise_level in config.mix.noise_levels
    ]


def _transient_probes(config: CorpusConfig) -> List[Probe]:
    transient = config.transient
    sweep_start, sweep_end = transient.kick_sweep_frequencies
    snare_decay = ExponentialDecayEnvelope(
        kind="exponential_decay",
        time_constant_seconds=transient.snare_decay_seconds,
    )
    kick_decay = ExponentialDecayEnvelope(
        kind="exponential_decay",
        time_constant_seconds=transient.kick_decay_seconds,
    )
    pluck_attack = LinearAttackEnvelope(
        kind="linear_attack",
        attack_seconds=transient.attack_seconds,
    )
    pluck_decay = ExponentialDecayEnvelope(
        kind="exponential_decay",
        time_constant_seconds=transient.attack_tone_decay_seconds,
    )
    kick_glide = ExponentialGlideOscillator(
        kind="exponential_glide",
        frequency_start=sweep_start,
        frequency_end=sweep_end,
        time_constant_seconds=transient.kick_decay_seconds,
    )
    reference_tone = SineOscillator(
        kind="sine",
        frequency=config.reference_frequency,
    )
    return [
        _unpitched(
            "transient-snare",
            TRANSIENT_CATEGORY,
            _voice(config, _layer(WhiteNoiseOscillator(kind="white_noise"), snare_decay)),
        ),
        _unpitched(
            "transient-kick",
            TRANSIENT_CATEGORY,
            _voice(config, _layer(kick_glide, kick_decay)),
        ),
        Probe(
            name="transient-pluck",
            category=TRANSIENT_CATEGORY,
            voice=_voice(config, _layer(reference_tone, pluck_attack, pluck_decay)),
            pitch=ProbePitch(
                frequency=config.reference_frequency, level_at=partial(_enveloped, (pluck_attack, pluck_decay))
            ),
        ),
    ]


def _crescendo_probe(config: CorpusConfig) -> Probe:
    return Probe(
        name="dynamics-crescendo",
        category=DYNAMICS_CATEGORY,
        voice=_voice(
            config,
            _layer(
                SineOscillator(kind="sine", frequency=config.reference_frequency),
                LinearRampEnvelope(kind="linear_ramp"),
            ),
        ),
        pitch=ProbePitch(frequency=config.reference_frequency, level_at=partial(_rising, config.item_seconds)),
    )


def _polyphony_probes(config: CorpusConfig) -> List[Probe]:
    polyphony = config.polyphony
    chord_gain = UNIT_GAIN / len(polyphony.chord_frequencies)
    chord = [
        _layer(SineOscillator(kind="sine", frequency=frequency), gain=chord_gain)
        for frequency in polyphony.chord_frequencies
    ]
    note_decay = PeriodicDecayEnvelope(
        kind="periodic_decay",
        period_seconds=polyphony.note_seconds,
        time_constant_seconds=polyphony.note_decay_seconds,
        delay_seconds=FIRST_STRIKE_SECONDS,
    )
    melody = [
        _layer(
            PulseOscillator(kind="pulse", frequency=frequency, duty_cycle=SQUARE_DUTY_CYCLE),
            GateEnvelope(
                kind="gate",
                start_seconds=index * polyphony.note_seconds,
                end_seconds=(index + 1) * polyphony.note_seconds,
            ),
            note_decay,
        )
        for index, frequency in enumerate(polyphony.melody_frequencies)
    ]
    snare = _layer(
        WhiteNoiseOscillator(kind="white_noise"),
        PeriodicDecayEnvelope(
            kind="periodic_decay",
            period_seconds=polyphony.snare_period_seconds,
            time_constant_seconds=polyphony.snare_decay_seconds,
            delay_seconds=polyphony.snare_delay_seconds,
        ),
        gain=polyphony.snare_level,
    )
    return [
        _unpitched("polyphony-chord", POLYPHONY_CATEGORY, _voice(config, *chord)),
        _unpitched("polyphony-melody-snare", POLYPHONY_CATEGORY, _voice(config, *melody, snare)),
    ]


def _burst_then_hiss_probe(config: CorpusConfig) -> Probe:
    dynamics = config.dynamics
    burst = _layer(
        WhiteNoiseOscillator(kind="white_noise"),
        GateEnvelope(kind="gate", start_seconds=FIRST_STRIKE_SECONDS, end_seconds=dynamics.burst_seconds),
        gain=config.noise.white_level,
    )
    hiss = _layer(
        WhiteNoiseOscillator(kind="white_noise"),
        GateEnvelope(kind="gate", start_seconds=dynamics.burst_seconds, end_seconds=config.item_seconds),
        gain=config.noise.white_level * dynamics.hiss_level,
    )
    return _unpitched("dynamics-burst-then-hiss", DYNAMICS_CATEGORY, _voice(config, burst, hiss))


def _bass_hi_hats_probe(config: CorpusConfig) -> Probe:
    mix = config.mix
    bass = _layer(SineOscillator(kind="sine", frequency=mix.bass_frequency))
    hats = _layer(
        WhiteNoiseOscillator(kind="white_noise"),
        PeriodicDecayEnvelope(
            kind="periodic_decay",
            period_seconds=mix.hat_period_seconds,
            time_constant_seconds=mix.hat_decay_seconds,
            delay_seconds=FIRST_STRIKE_SECONDS,
        ),
        gain=mix.hat_level,
    )
    return Probe(
        name="mix-bass-hi-hats",
        category=MIX_CATEGORY,
        voice=_voice(config, bass, hats),
        pitch=_steady_pitch(mix.bass_frequency),
    )


def _unpitched(name: str, category: str, voice: Voice) -> Probe:
    """A probe holding no single pitch."""
    return Probe(name=name, category=category, voice=voice, pitch=None)


def _steady_pitch(frequency: float) -> ProbePitch:
    """The pitch of a tone holding ``frequency`` at its full level throughout."""
    return ProbePitch(frequency=frequency, level_at=partial(_enveloped, ()))


def _enveloped(envelopes: Sequence[EnvelopeUnion], times: np.ndarray) -> np.ndarray:
    """The level ``envelopes`` shape a tone to at each time, against its full level: their product."""
    level = np.ones_like(times)
    for envelope in envelopes:
        level = level * envelope.render(times)

    return level


def _rising(seconds: float, times: np.ndarray) -> np.ndarray:
    """The level of a tone rising evenly from silence to its full level over ``seconds``, at each time."""
    return times / seconds


def _layer(
    oscillator: OscillatorUnion,
    *envelopes: EnvelopeUnion,
    gain: float = UNIT_GAIN,
) -> Layer:
    return Layer(oscillator=oscillator, envelopes=envelopes, gain=gain)


def _voice(config: CorpusConfig, *layers: Layer) -> Voice:
    return Voice(
        duration_seconds=config.item_seconds,
        layers=layers,
        filters=(),
    )


def _item(
    rendered: RenderedProbe,
    frame_rate: int,
    config: CorpusConfig,
    truth: TruthConfig,
) -> CorpusItem:
    """
    Assemble a corpus item from a rendered probe heard as one recording.

    The probe is brought to the corpus level, clipped to the valid wave
    range, and stored as float32, so every item shares one loudness convention.
    """
    probe = rendered.probe
    return CorpusItem(
        name=probe.name,
        family=probe.family,
        category=probe.category,
        listed=True,
        audio=clip_audio(at_corpus_level(rendered.audio, config)).astype(np.float32),
        truth=probe_truth(rendered, frame_rate, truth),
        channels=None,
        stems=None,
    )


def probe_truth(rendered: RenderedProbe, frame_rate: int, truth: TruthConfig) -> Optional[Truth]:
    """The truth of a rendered probe: the one line of the pitch its tone holds, ``None`` for a probe holding none.

    The line covers every frame the render reaches into, and is silent where the tone falls below the
    audible range. Every sound made of the probe carries this one truth.

    Args:
        rendered: The probe as the corpus pass renders it.
        frame_rate: The frames per second the line is written at.
        truth: How the line counts the tone as sounding.

    Returns:
        Optional[Truth]: The probe's one line, or ``None`` for a probe holding no single pitch.
    """
    pitch = rendered.probe.pitch
    if pitch is None:
        return None

    frames = frames_reached(rendered.samples, rendered.sample_rate, frame_rate)
    sounding_at = partial(audible, pitch.level_at, truth.audible_floor)
    line = pitch_line(partial(steady, pitch.frequency), sounding_at, frames, frame_rate)
    return Truth(instructions={}, pitches={LINE: line})
