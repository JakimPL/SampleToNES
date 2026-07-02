from typing import Final

import numpy as np
from scipy.signal import butter, sosfilt

from sampletones_core.audio.processing import normalize
from sampletones_core.utils.frequencies import pitch_to_frequency

SEED: Final[int] = 1337
HIGHPASS_ORDER: Final[int] = 4
KICK_PITCH: Final[int] = 45
KICK_DURATION: Final[float] = 0.5
KICK_DECAY: Final[float] = 6.0
HIHAT_DURATION: Final[float] = 0.35
HIHAT_CUTOFF_HZ: Final[float] = 8000.0
HIHAT_DECAY: Final[float] = 9.0


def _length(duration: float, sample_rate: int) -> int:
    return round(duration * sample_rate)


def _exponential_decay(length: int, decay: float) -> np.ndarray:
    """An amplitude envelope falling from 1 to exp(-decay) over the sample."""
    ramp = np.linspace(0.0, 1.0, length, dtype=np.float32)
    return np.exp(-decay * ramp).astype(np.float32)


def sine(frequency: float, duration: float, sample_rate: int) -> np.ndarray:
    time_axis = np.arange(_length(duration, sample_rate), dtype=np.float32) / sample_rate
    return np.sin(2.0 * np.pi * frequency * time_axis).astype(np.float32)


def synth_kick(
    *,
    sample_rate: int,
    duration: float = KICK_DURATION,
    pitch: int = KICK_PITCH,
    decay: float = KICK_DECAY,
) -> np.ndarray:
    """A kick: a sine at ``pitch`` shaped by an exponential amplitude decay."""
    tone = sine(pitch_to_frequency(pitch), duration, sample_rate)
    envelope = _exponential_decay(len(tone), decay)
    return normalize((tone * envelope).astype(np.float32))


def synth_hihat(
    *,
    sample_rate: int,
    duration: float = HIHAT_DURATION,
    cutoff_hz: float = HIHAT_CUTOFF_HZ,
    decay: float = HIHAT_DECAY,
    seed: int = SEED,
) -> np.ndarray:
    """A hihat: seeded white noise, high-pass filtered, shaped by a fast decay."""
    length = _length(duration, sample_rate)
    noise = np.random.default_rng(seed).standard_normal(length).astype(np.float32)
    sections = butter(HIGHPASS_ORDER, cutoff_hz, btype="highpass", fs=sample_rate, output="sos")
    filtered = sosfilt(sections, noise).astype(np.float32)
    envelope = _exponential_decay(length, decay)
    return normalize((filtered * envelope).astype(np.float32))
