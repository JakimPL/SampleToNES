from typing import Final, List, Tuple

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

from .item import CorpusItem

Probe = Tuple[str, str, Voice]

UNIT_GAIN: Final[float] = 1.0
SQUARE_DUTY_CYCLE: Final[float] = 0.5
FIRST_STRIKE_SECONDS: Final[float] = 0.0


def build_corpus(
    sample_rate: int,
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

    Args:
        sample_rate: Sampling rate of the synthesized items in Hz.
        config: Corpus tuning holding the probe parameters per signal class.

    Returns:
        The corpus items, each carrying its category for per-class reporting.
    """
    generator = np.random.default_rng(config.seed)
    probes: List[Probe] = [
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
    return [
        _item(
            name,
            category,
            voice.render(sample_rate=sample_rate, generator=generator),
            config,
        )
        for name, category, voice in probes
    ]


def _tone_probes(config: CorpusConfig) -> List[Probe]:
    return [
        (
            f"tone-{frequency:g}hz",
            "tone",
            _voice(
                config,
                _layer(
                    SineOscillator(
                        kind="sine",
                        frequency=frequency,
                    )
                ),
            ),
        )
        for frequency in config.tone.frequencies
    ]


def _timbre_probes(config: CorpusConfig) -> List[Probe]:
    return [
        (
            f"pulse-duty{duty_cycle:g}",
            "timbre",
            _voice(
                config,
                _layer(
                    PulseOscillator(
                        kind="pulse",
                        frequency=config.timbre.frequency,
                        duty_cycle=duty_cycle,
                    )
                ),
            ),
        )
        for duty_cycle in config.timbre.duty_cycles
    ]


def _noise_probes(config: CorpusConfig) -> List[Probe]:
    return [
        (
            "noise-white",
            "noise",
            _voice(
                config,
                _layer(
                    WhiteNoiseOscillator(kind="white_noise"),
                    gain=config.noise.white_level,
                ),
            ),
        ),
        (
            "noise-dark",
            "noise",
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
        (
            f"mix-noise{noise_level:g}",
            "mix",
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
        (
            "transient-snare",
            "transient",
            _voice(config, _layer(WhiteNoiseOscillator(kind="white_noise"), snare_decay)),
        ),
        (
            "transient-kick",
            "transient",
            _voice(config, _layer(kick_glide, kick_decay)),
        ),
        (
            "transient-pluck",
            "transient",
            _voice(config, _layer(reference_tone, pluck_attack, pluck_decay)),
        ),
    ]


def _crescendo_probe(config: CorpusConfig) -> Probe:
    return (
        "dynamics-crescendo",
        "dynamics",
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
        ("polyphony-chord", "polyphony", _voice(config, *chord)),
        ("polyphony-melody-snare", "polyphony", _voice(config, *melody, snare)),
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
    return ("dynamics-burst-then-hiss", "dynamics", _voice(config, burst, hiss))


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
    return ("mix-bass-hi-hats", "mix", _voice(config, bass, hats))


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
    name: str,
    category: str,
    audio: np.ndarray,
    config: CorpusConfig,
) -> CorpusItem:
    """
    Assemble a corpus item from a unit-scale probe.

    The probe is scaled by the corpus amplitude, clipped to the valid wave
    range, and stored as float32, so every item shares one loudness convention.
    """
    scaled = clip_audio(config.amplitude * audio)
    return CorpusItem(
        name=name,
        category=category,
        audio=scaled.astype(np.float32),
    )
