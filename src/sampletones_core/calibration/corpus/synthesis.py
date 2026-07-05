from typing import List

import numpy as np

from sampletones_core.audio.processing import clip_audio
from sampletones_core.calibration.config.corpus import CorpusConfig
from sampletones_core.calibration.config.transient import TransientConfig

from .item import CorpusItem


def build_corpus(
    sample_rate: int,
    *,
    config: CorpusConfig,
) -> List[CorpusItem]:
    """
    Synthesize the calibration probe corpus.

    The corpus spans the signal classes the criterion must arbitrate between:
    steady tones across the pitch range, pulse timbres of several duty cycles,
    broadband noise, tone-plus-noise mixes, percussive transients, and a
    crescendo probing the dynamic range. Every item is deterministic for a
    fixed sample rate and configuration, so referee scores are reproducible
    across runs.

    Args:
        sample_rate: Sampling rate of the synthesized items in Hz.
        config: Corpus tuning holding the probe parameters per signal class.

    Returns:
        The corpus items, each carrying its category for per-class reporting.
    """
    generator = np.random.default_rng(config.seed)
    time = np.arange(int(config.item_seconds * sample_rate)) / sample_rate

    items: List[CorpusItem] = []
    items.extend(_tones(time, config))
    items.extend(_pulse_timbres(time, config))
    items.extend(_noises(generator, time.shape[0], config))
    items.extend(_tone_noise_mixes(generator, time, config))
    items.extend(_transients(generator, time, sample_rate, config))
    items.append(_crescendo(time, config))

    return items


def _tones(time: np.ndarray, config: CorpusConfig) -> List[CorpusItem]:
    return [
        _item(
            f"tone-{frequency:g}hz",
            "tone",
            _sine(frequency, time),
            config,
        )
        for frequency in config.tone.frequencies
    ]


def _pulse_timbres(time: np.ndarray, config: CorpusConfig) -> List[CorpusItem]:
    phase = (config.timbre.frequency * time) % 1.0
    return [
        _item(
            f"pulse-duty{duty_cycle:g}",
            "timbre",
            np.where(phase < duty_cycle, 1.0, -1.0),
            config,
        )
        for duty_cycle in config.timbre.duty_cycles
    ]


def _noises(generator: np.random.Generator, length: int, config: CorpusConfig) -> List[CorpusItem]:
    """
    White and dark noise probes.

    The dark probe is a mean-centered random walk normalized to unit peak: its
    spectrum falls off towards high frequencies, probing the opposite end of
    the noise-color axis from the white probe.
    """
    white = config.noise.white_level * generator.standard_normal(length)
    dark = np.cumsum(generator.standard_normal(length))
    dark = dark - np.mean(dark)
    dark = dark / np.max(np.abs(dark))
    return [
        _item("noise-white", "noise", white, config),
        _item("noise-dark", "noise", dark, config),
    ]


def _tone_noise_mixes(generator: np.random.Generator, time: np.ndarray, config: CorpusConfig) -> List[CorpusItem]:
    tone = _sine(config.reference_frequency, time)
    return [
        _item(
            f"mix-noise{noise_level:g}",
            "mix",
            tone + noise_level * generator.standard_normal(time.shape[0]),
            config,
        )
        for noise_level in config.mix.noise_levels
    ]


def _transients(
    generator: np.random.Generator,
    time: np.ndarray,
    sample_rate: int,
    config: CorpusConfig,
) -> List[CorpusItem]:
    return [
        _item("transient-snare", "transient", _snare(generator, time, config.transient), config),
        _item("transient-kick", "transient", _kick(time, sample_rate, config.transient), config),
        _item("transient-pluck", "transient", _pluck(time, config), config),
    ]


def _snare(generator: np.random.Generator, time: np.ndarray, transient: TransientConfig) -> np.ndarray:
    return generator.standard_normal(time.shape[0]) * np.exp(-time / transient.snare_decay_seconds)


def _kick(time: np.ndarray, sample_rate: int, transient: TransientConfig) -> np.ndarray:
    """Sine glide between the sweep frequencies, decaying together with its pitch."""
    sweep_start, sweep_end = transient.kick_sweep_frequencies
    decay = np.exp(-time / transient.kick_decay_seconds)
    sweep = sweep_end + (sweep_start - sweep_end) * decay
    phase = 2.0 * np.pi * np.cumsum(sweep) / sample_rate
    kick: np.ndarray = np.sin(phase) * decay
    return kick


def _pluck(time: np.ndarray, config: CorpusConfig) -> np.ndarray:
    attack = np.minimum(time / config.transient.attack_seconds, 1.0)
    envelope = attack * np.exp(-time / config.transient.attack_tone_decay_seconds)
    pluck: np.ndarray = _sine(config.reference_frequency, time) * envelope
    return pluck


def _crescendo(time: np.ndarray, config: CorpusConfig) -> CorpusItem:
    ramp = time / time[-1]
    return _item("dynamics-crescendo", "dynamics", _sine(config.reference_frequency, time) * ramp, config)


def _sine(frequency: float, time: np.ndarray) -> np.ndarray:
    return np.sin(2.0 * np.pi * frequency * time)


def _item(name: str, category: str, audio: np.ndarray, config: CorpusConfig) -> CorpusItem:
    """
    Assemble a corpus item from a unit-scale probe.

    The probe is scaled by the corpus amplitude, clipped to the valid wave
    range, and stored as float32, so every item shares one loudness convention.
    """
    scaled = clip_audio(config.amplitude * audio)
    return CorpusItem(name=name, category=category, audio=scaled.astype(np.float32))
