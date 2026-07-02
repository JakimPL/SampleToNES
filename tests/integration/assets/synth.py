from typing import Callable, Dict, Final

import numpy as np
from scipy.signal import butter, sosfilt

from sampletones_core.audio.processing import normalize
from sampletones_core.utils.frequencies import pitch_to_frequency
from tests.integration.assets.synth_config import (
    NoiseConfig,
    SynthConfig,
    SynthKind,
    ToneConfig,
)

HIGHPASS_FILTER: Final[str] = "highpass"


def _length(duration: float, sample_rate: int) -> int:
    return round(duration * sample_rate)


def _exponential_decay(length: int, decay: float) -> np.ndarray:
    """An amplitude envelope falling from 1 to exp(-decay) over the sample."""
    ramp = np.linspace(0.0, 1.0, length, dtype=np.float32)
    return np.exp(-decay * ramp).astype(np.float32)


def swept_sine(pitch_start: int, pitch_end: int, duration: float, sample_rate: int) -> np.ndarray:
    """A sine whose pitch glides linearly (in semitones) from start to end.

    The instantaneous frequency follows a log-linear ramp between the endpoint
    pitches, integrated into phase so the waveform stays continuous.
    """
    length = _length(duration, sample_rate)
    ramp = np.linspace(0.0, 1.0, length, dtype=np.float64)
    frequency_start = pitch_to_frequency(pitch_start)
    frequency_end = pitch_to_frequency(pitch_end)
    frequencies = frequency_start * (frequency_end / frequency_start) ** ramp
    phase = np.cumsum(2.0 * np.pi * frequencies / sample_rate)
    return np.sin(phase).astype(np.float32)


def synth_tone(config: ToneConfig, *, sample_rate: int) -> np.ndarray:
    """A tone: a pitch sweep from ``pitch_start`` to ``pitch_end`` under an exponential decay."""
    tone = swept_sine(config.pitch_start, config.pitch_end, config.duration, sample_rate)
    envelope = _exponential_decay(len(tone), config.decay)
    return normalize((tone * envelope).astype(np.float32))


def synth_noise(config: NoiseConfig, *, sample_rate: int, seed: int) -> np.ndarray:
    """Seeded white noise, high-pass filtered, shaped by a fast decay."""
    length = _length(config.duration, sample_rate)
    noise = np.random.default_rng(seed).standard_normal(length).astype(np.float32)
    sections = butter(config.highpass_order, config.cutoff_hz, btype=HIGHPASS_FILTER, fs=sample_rate, output="sos")
    filtered = sosfilt(sections, noise).astype(np.float32)
    envelope = _exponential_decay(length, config.decay)
    return normalize((filtered * envelope).astype(np.float32))


def _kick(config: SynthConfig, *, sample_rate: int) -> np.ndarray:
    return synth_tone(config.kick, sample_rate=sample_rate)


def _lead(config: SynthConfig, *, sample_rate: int) -> np.ndarray:
    return synth_tone(config.lead, sample_rate=sample_rate)


def _hihat(config: SynthConfig, *, sample_rate: int) -> np.ndarray:
    return synth_noise(config.hihat, sample_rate=sample_rate, seed=config.seed)


SYNTHS: Final[Dict[SynthKind, Callable[..., np.ndarray]]] = {
    SynthKind.KICK: _kick,
    SynthKind.LEAD: _lead,
    SynthKind.HIHAT: _hihat,
}
