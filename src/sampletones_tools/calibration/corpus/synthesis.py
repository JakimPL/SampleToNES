from dataclasses import dataclass
from typing import Dict, Final, List, Optional

import numpy as np

from sampletones_core.audio.processing import clip_audio
from sampletones_tools.calibration.config.corpus import CorpusConfig
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
from .truth import LINE, PitchLine, Truth, frames_covering

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
class Probe:
    """A probe of the corpus: its name and category, the voice it renders, and the pitch it holds.

    Attributes:
        name: The name its files are written under.
        category: The kind of decision it tests.
        voice: What it renders.
        frequency: The pitch in Hz it holds throughout, or ``None`` for a probe whose pitch the corpus
            leaves unstated.
    """

    name: str
    category: str
    voice: Voice
    frequency: Optional[float]

    @property
    def family(self) -> Family:
        """The family the probe's category belongs to."""
        return PROBE_FAMILIES[self.category]


def build_corpus(
    sample_rate: int,
    frame_rate: int,
    *,
    config: CorpusConfig,
) -> List[CorpusItem]:
    """
    Synthesize the calibration probe corpus.

    The corpus spans the signal classes the criterion must arbitrate between:
    steady tones across the pitch range, pulse timbres of several duty cycles,
    broadband noise, tone-plus-noise mixes, percussive transients, level changes
    (a crescendo and a burst dropping to a hiss), and voices sounding together.
    Probes render in a fixed order from
    one seeded generator, so every item is deterministic for a fixed sample
    rate and configuration and referee scores are reproducible across runs.
    The sine tones and the pulse waves hold one pitch throughout, and carry it
    as their truth; the other probes' truth is ``None``.

    Args:
        sample_rate: Sampling rate of the synthesized items in Hz.
        frame_rate: The frames per second a pitch line is written at.
        config: Corpus tuning holding the probe parameters per signal class.

    Returns:
        The corpus items, each carrying its category for per-class reporting.
    """
    generator = np.random.default_rng(config.seed)
    return [
        _item(
            probe,
            probe.voice.render(sample_rate=sample_rate, generator=generator),
            frame_rate,
            config,
        )
        for probe in corpus_probes(config)
    ]


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
            frequency=frequency,
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
            frequency=config.timbre.frequency,
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
        _unpitched(
            f"mix-noise{noise_level:g}",
            MIX_CATEGORY,
            _voice(
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
        _unpitched(
            "transient-pluck",
            TRANSIENT_CATEGORY,
            _voice(config, _layer(reference_tone, pluck_attack, pluck_decay)),
        ),
    ]


def _crescendo_probe(config: CorpusConfig) -> Probe:
    return _unpitched(
        "dynamics-crescendo",
        DYNAMICS_CATEGORY,
        _voice(
            config,
            _layer(
                SineOscillator(kind="sine", frequency=config.reference_frequency),
                LinearRampEnvelope(kind="linear_ramp"),
            ),
        ),
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
    return _unpitched("mix-bass-hi-hats", MIX_CATEGORY, _voice(config, bass, hats))


def _unpitched(name: str, category: str, voice: Voice) -> Probe:
    """A probe whose pitch the corpus leaves unstated."""
    return Probe(name=name, category=category, voice=voice, frequency=None)


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
    probe: Probe,
    audio: np.ndarray,
    frame_rate: int,
    config: CorpusConfig,
) -> CorpusItem:
    """
    Assemble a corpus item from a unit-scale probe.

    The probe is scaled by the corpus amplitude, clipped to the valid wave
    range, and stored as float32, so every item shares one loudness convention.
    """
    scaled = clip_audio(config.amplitude * audio)
    return CorpusItem(
        name=probe.name,
        family=probe.family,
        category=probe.category,
        listed=True,
        audio=scaled.astype(np.float32),
        truth=_steady_truth(probe, frames_covering(config.item_seconds, frame_rate)),
        channels=None,
        stems=None,
    )


def _steady_truth(probe: Probe, frames: int) -> Optional[Truth]:
    """The probe's one line, holding its pitch in each of ``frames`` frames, where it holds one."""
    if probe.frequency is None:
        return None

    line: PitchLine = (probe.frequency,) * frames
    return Truth(instructions={}, pitches={LINE: line})
