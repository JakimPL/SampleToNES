from typing import Final

import numpy as np
import pytest

from sampletones_tools.synthesis.oscillators.sine import SineOscillator
from sampletones_tools.synthesis.oscillators.vibrato import VibratoOscillator

FREQUENCY: Final[float] = 220.0
RATE: Final[float] = 5.0
DEPTH: Final[float] = 50.0


def _vibrato(depth: float, harmonic: int) -> VibratoOscillator:
    return VibratoOscillator(kind="vibrato", frequency=FREQUENCY, rate_hertz=RATE, depth_cents=depth, harmonic=harmonic)


class TestVibratoOscillator:
    def test_without_depth_it_sounds_the_steady_sine(
        self, time_axis: np.ndarray, generator: np.random.Generator
    ) -> None:
        steady = SineOscillator(kind="sine", frequency=FREQUENCY).render(time_axis - time_axis[0], generator=generator)

        np.testing.assert_allclose(_vibrato(0.0, 1).render(time_axis, generator=generator), steady, atol=1e-6)

    def test_the_pitch_swings_by_its_depth_either_way(self, time_axis: np.ndarray) -> None:
        cents = 1200 * np.log2(_vibrato(DEPTH, 1).frequency_at(time_axis) / FREQUENCY)

        assert float(np.max(cents)) == pytest.approx(DEPTH, abs=0.5)
        assert float(np.min(cents)) == pytest.approx(-DEPTH, abs=0.5)

    def test_a_harmonic_sounds_its_multiple_of_the_fundamental(
        self,
        time_axis: np.ndarray,
        sample_rate: int,
        generator: np.random.Generator,
    ) -> None:
        audio = _vibrato(0.0, 3).render(time_axis, generator=generator)
        spectrum = np.abs(np.fft.rfft(audio))
        peak = np.fft.rfftfreq(audio.shape[0], 1.0 / sample_rate)[np.argmax(spectrum)]

        assert peak == pytest.approx(3 * FREQUENCY, abs=1.0)
