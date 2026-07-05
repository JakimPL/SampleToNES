from typing import Protocol

import numpy as np


class Oscillator(Protocol):
    """Unit-scale waveform source rendered over a time axis in seconds."""

    def render(self, time: np.ndarray, *, generator: np.random.Generator) -> np.ndarray: ...


class Envelope(Protocol):
    """Multiplicative amplitude shape rendered over a time axis in seconds."""

    def render(self, time: np.ndarray) -> np.ndarray: ...


class AudioFilter(Protocol):
    """Spectral shaping applied to a rendered waveform."""

    def apply(self, audio: np.ndarray, *, sample_rate: int) -> np.ndarray: ...
