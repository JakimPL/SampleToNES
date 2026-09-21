from dataclasses import dataclass
from typing import Final

import numpy as np
import pytest
from scipy.signal import sawtooth

from sampletones_tools.calibration.config.referee import RefereeConfig

SAMPLE_RATE: Final[int] = 22050
SIGNAL_SECONDS: Final[float] = 1.0
TONE_FREQUENCY: Final[float] = 220.0
TONE_AMPLITUDE: Final[float] = 0.3
SEMITONE_RATIO: Final[float] = 2.0 ** (1.0 / 12.0)
TRIANGLE_WIDTH: Final[float] = 0.5
PLUCK_ATTACK_SECONDS: Final[float] = 0.005
PLUCK_DECAY_SECONDS: Final[float] = 0.3
ROLL_SECONDS: Final[float] = 0.005
NOISE_SEED: Final[int] = 5


def decibels_to_gain(decibels: float) -> float:
    return float(10.0 ** (decibels / 20.0))


def root_mean_square(audio: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(audio))))


@dataclass(frozen=True)
class ProbeSignals:
    """Probe signals around a steady tone and a plucked one, sharing one time axis.

    Attributes:
        sine: The reference tone.
        noise: White noise at the tone's RMS, scaled by a gain to reach a level under it.
        pluck: The reference tone with a short attack and an exponential decay.
    """

    time: np.ndarray
    sine: np.ndarray
    noise: np.ndarray
    pluck: np.ndarray

    @property
    def silence(self) -> np.ndarray:
        return np.zeros_like(self.sine)

    def tone(self, frequency: float) -> np.ndarray:
        return TONE_AMPLITUDE * np.sin(2.0 * np.pi * frequency * self.time)

    def triangle(self) -> np.ndarray:
        wave = sawtooth(2.0 * np.pi * TONE_FREQUENCY * self.time, TRIANGLE_WIDTH)
        return wave * root_mean_square(self.sine) / root_mean_square(wave)

    def pulse(self) -> np.ndarray:
        return TONE_AMPLITUDE * np.sign(np.sin(2.0 * np.pi * TONE_FREQUENCY * self.time))

    def hissing(self, signal: np.ndarray, decibels: float) -> np.ndarray:
        """The signal with white noise ``decibels`` under the steady tone's RMS."""
        return signal + self.noise * decibels_to_gain(decibels)

    def rolled_pluck(self) -> np.ndarray:
        return np.roll(self.pluck, round(ROLL_SECONDS * SAMPLE_RATE))


@pytest.fixture(scope="session")
def referee_config() -> RefereeConfig:
    return RefereeConfig.load()


@pytest.fixture(scope="session")
def probes() -> ProbeSignals:
    time = np.arange(round(SIGNAL_SECONDS * SAMPLE_RATE)) / SAMPLE_RATE
    sine = TONE_AMPLITUDE * np.sin(2.0 * np.pi * TONE_FREQUENCY * time)
    noise = np.random.default_rng(NOISE_SEED).standard_normal(time.shape[0])
    envelope = np.minimum(time / PLUCK_ATTACK_SECONDS, 1.0) * np.exp(-time / PLUCK_DECAY_SECONDS)
    return ProbeSignals(
        time=time,
        sine=sine,
        noise=noise * root_mean_square(sine) / root_mean_square(noise),
        pluck=sine * envelope,
    )
