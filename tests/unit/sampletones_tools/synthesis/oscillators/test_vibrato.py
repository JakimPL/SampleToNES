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

    @pytest.mark.parametrize("harmonic", [1, 3], ids=["fundamental", "third_partial"])
    def test_the_top_frequency_is_the_highest_the_partial_reaches(self, harmonic: int, time_axis: np.ndarray) -> None:
        highest = harmonic * float(np.max(_vibrato(DEPTH, harmonic).frequency_at(time_axis)))

        assert _vibrato(DEPTH, harmonic).top_frequency == pytest.approx(highest, rel=1e-6)

    def test_without_depth_the_top_frequency_is_the_partial_s_own(self) -> None:
        assert _vibrato(0.0, 3).top_frequency == pytest.approx(3 * FREQUENCY)

    def test_the_swing_starts_upward_from_the_frequency(self, time_axis: np.ndarray) -> None:
        frequency = _vibrato(DEPTH, 1).frequency_at(time_axis[:2])

        assert frequency[0] == pytest.approx(FREQUENCY)
        assert frequency[1] > FREQUENCY

    def test_the_phase_starts_at_zero(self, time_axis: np.ndarray, generator: np.random.Generator) -> None:
        assert _vibrato(DEPTH, 3).render(time_axis, generator=generator)[0] == 0.0

    @pytest.mark.parametrize("samples", [0, 1], ids=["no_samples", "one_sample"])
    def test_an_axis_of_no_step_renders_silence(
        self, samples: int, time_axis: np.ndarray, generator: np.random.Generator
    ) -> None:
        audio = _vibrato(DEPTH, 1).render(time_axis[:samples], generator=generator)

        assert audio.shape == (samples,) and not np.any(audio)
