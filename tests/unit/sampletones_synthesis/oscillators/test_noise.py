from typing import Final

import numpy as np
import pytest

from sampletones_synthesis.oscillators.walk_noise import WalkNoiseOscillator
from sampletones_synthesis.oscillators.white_noise import WhiteNoiseOscillator

SEED: Final[int] = 99


class TestWhiteNoiseOscillator:
    def test_same_seed_reproduces_the_waveform(self, time_axis: np.ndarray) -> None:
        oscillator = WhiteNoiseOscillator(kind="white_noise")
        first = oscillator.render(time_axis, generator=np.random.default_rng(SEED))
        second = oscillator.render(time_axis, generator=np.random.default_rng(SEED))
        assert np.array_equal(first, second)

    def test_unit_standard_deviation(self, time_axis: np.ndarray, generator: np.random.Generator) -> None:
        audio = WhiteNoiseOscillator(kind="white_noise").render(time_axis, generator=generator)
        assert np.std(audio) == pytest.approx(1.0, abs=0.05)


class TestWalkNoiseOscillator:
    def test_zero_mean_and_unit_peak(self, time_axis: np.ndarray, generator: np.random.Generator) -> None:
        audio = WalkNoiseOscillator(kind="walk_noise").render(time_axis, generator=generator)
        assert np.mean(audio) == pytest.approx(0.0, abs=1e-9)
        assert np.max(np.abs(audio)) == pytest.approx(1.0)

    def test_energy_concentrates_at_low_frequencies(
        self,
        time_axis: np.ndarray,
        generator: np.random.Generator,
    ) -> None:
        audio = WalkNoiseOscillator(kind="walk_noise").render(time_axis, generator=generator)
        spectrum = np.abs(np.fft.rfft(audio)) ** 2
        half = spectrum.shape[0] // 2
        assert np.sum(spectrum[:half]) > 10.0 * np.sum(spectrum[half:])
