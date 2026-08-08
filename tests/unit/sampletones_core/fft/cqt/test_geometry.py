from dataclasses import dataclass
from typing import List

import numpy as np
import pytest

from sampletones_core.fft.cqt.frequencies import calculate_cqt_frequencies
from sampletones_core.fft.cqt.geometry import (
    calculate_wavelet_lengths,
    quality_factor,
    resolvable_bins,
)
from sampletones_core.fft.utils import calculate_n_bins
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase


class TestQualityFactor(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        bins_per_octave: int
        expected: float

        @property
        def label(self) -> str:
            return f"bpo_{self.bins_per_octave}"

    test_cases = [
        TestCase(bins_per_octave=1, expected=1.0),
        TestCase(bins_per_octave=12, expected=16.817154),
        TestCase(bins_per_octave=24, expected=34.127088),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_quality_factor(self, test_case: TestCase) -> None:
        assert quality_factor(test_case.bins_per_octave) == pytest.approx(test_case.expected, rel=1e-6)

    def test_more_bins_raise_quality(self) -> None:
        assert quality_factor(48) > quality_factor(24) > quality_factor(12)


class TestCalculateWaveletLengths(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        sample_rate: int
        frequencies: List[float]
        expected: List[float]

        @property
        def label(self) -> str:
            return f"rate_{self.sample_rate}"

    test_cases = [
        TestCase(
            sample_rate=11025,
            frequencies=[55.0, 110.0, 220.0, 440.0],
            expected=[3372.0, 1686.0, 843.0, 422.0],
        ),
        TestCase(
            sample_rate=22050,
            frequencies=[55.0, 110.0, 220.0, 440.0],
            expected=[6743.0, 3372.0, 1686.0, 843.0],
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_calculate_wavelet_lengths(self, test_case: TestCase) -> None:
        lengths = calculate_wavelet_lengths(np.array(test_case.frequencies), test_case.sample_rate, bins_per_octave=12)
        assert lengths.tolist() == test_case.expected

    def test_halving_frequency_doubles_length(self) -> None:
        frequencies = np.array([100.0, 50.0])
        lengths = calculate_wavelet_lengths(frequencies, sample_rate=16000, bins_per_octave=12)
        assert lengths[1] == pytest.approx(2.0 * lengths[0], abs=1.0)


class TestResolvableBins(BaseTestSuite):
    CUTOFF = 1789773.0 / 0x8000

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        sample_rate: int
        signal_length: int
        expected: int

        @property
        def label(self) -> str:
            return f"rate_{self.sample_rate}_len_{self.signal_length}"

    test_cases = [
        TestCase(sample_rate=11025, signal_length=3395, expected=0),
        TestCase(sample_rate=11025, signal_length=848, expected=25),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_unresolvable_count(self, test_case: TestCase) -> None:
        n_bins = calculate_n_bins(test_case.sample_rate, self.CUTOFF, bins_per_octave=12)
        frequencies = calculate_cqt_frequencies(n_bins, self.CUTOFF, bins_per_octave=12)
        mask = resolvable_bins(
            frequencies,
            test_case.sample_rate,
            test_case.signal_length,
            bins_per_octave=12,
        )
        assert int((~mask).sum()) == test_case.expected

    def test_unresolvable_bins_are_the_lowest(self) -> None:
        sample_rate, signal_length = 11025, 848
        n_bins = calculate_n_bins(sample_rate, self.CUTOFF, bins_per_octave=12)
        frequencies = calculate_cqt_frequencies(n_bins, self.CUTOFF, bins_per_octave=12)
        mask = resolvable_bins(frequencies, sample_rate, signal_length, bins_per_octave=12)
        first_resolvable = int(np.argmax(mask))
        assert not mask[:first_resolvable].any()
        assert mask[first_resolvable:].all()

    def test_boundary_frequency_is_resolvable(self) -> None:
        sample_rate, signal_length = 16000, 4000
        floor = quality_factor(12) * sample_rate / signal_length
        mask = resolvable_bins(np.array([floor]), sample_rate, signal_length, bins_per_octave=12)
        assert bool(mask[0])
