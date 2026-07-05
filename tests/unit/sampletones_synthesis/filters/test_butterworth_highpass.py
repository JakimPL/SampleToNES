from typing import Final

import numpy as np

from sampletones_synthesis.filters.butterworth_highpass import ButterworthHighpassFilter

CUTOFF_HZ: Final[float] = 2000.0
ORDER: Final[int] = 4
LOW_FREQUENCY: Final[float] = 100.0
HIGH_FREQUENCY: Final[float] = 8000.0


def _rms(audio: np.ndarray) -> float:
    return float(np.sqrt(np.mean(audio**2)))


class TestButterworthHighpassFilter:
    def test_attenuates_below_and_preserves_above_the_cutoff(
        self,
        time_axis: np.ndarray,
        sample_rate: int,
    ) -> None:
        highpass = ButterworthHighpassFilter(kind="butterworth_highpass", cutoff_hz=CUTOFF_HZ, order=ORDER)
        low = np.sin(2.0 * np.pi * LOW_FREQUENCY * time_axis)
        high = np.sin(2.0 * np.pi * HIGH_FREQUENCY * time_axis)

        low_ratio = _rms(highpass.apply(low, sample_rate=sample_rate)) / _rms(low)
        high_ratio = _rms(highpass.apply(high, sample_rate=sample_rate)) / _rms(high)

        assert low_ratio < 0.01
        assert high_ratio > 0.9
