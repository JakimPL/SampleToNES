from typing import Final

import numpy as np
import pytest

from sampletones_synthesis.oscillators.sine import SineOscillator

FREQUENCY: Final[float] = 440.0


class TestSineOscillator:
    def test_spectrum_peaks_at_the_configured_frequency(
        self,
        time_axis: np.ndarray,
        sample_rate: int,
        generator: np.random.Generator,
    ) -> None:
        oscillator = SineOscillator(kind="sine", frequency=FREQUENCY)
        audio = oscillator.render(time_axis, generator=generator)
        spectrum = np.abs(np.fft.rfft(audio))
        peak_frequency = np.fft.rfftfreq(audio.shape[0], 1.0 / sample_rate)[np.argmax(spectrum)]
        assert peak_frequency == pytest.approx(FREQUENCY, abs=1.0)

    def test_unit_amplitude_and_float64(
        self,
        time_axis: np.ndarray,
        generator: np.random.Generator,
    ) -> None:
        audio = SineOscillator(kind="sine", frequency=FREQUENCY).render(time_axis, generator=generator)
        assert audio.dtype == np.float64
        assert np.max(np.abs(audio)) == pytest.approx(1.0, abs=1e-6)

    def test_pitch_specification_matches_its_frequency(
        self,
        time_axis: np.ndarray,
        generator: np.random.Generator,
    ) -> None:
        from_pitch = SineOscillator(kind="sine", frequency=69).render(time_axis, generator=generator)
        from_hertz = SineOscillator(kind="sine", frequency=440.0).render(time_axis, generator=generator)
        assert np.array_equal(from_pitch, from_hertz)
