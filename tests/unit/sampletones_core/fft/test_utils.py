from dataclasses import dataclass
from typing import Any, Optional, Tuple, Type, Union

import numpy as np
import pytest

from sampletones_core.fft.utils import (
    calculate_n_bins,
    to_resolution_floored_log_bands,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase, BaseRegularTestCase
from tests.suite.errors import expect_error


class TestCalculateNBins(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Union[int, Type[Exception]]
        sample_rate: int
        cutoff: float
        bins_per_octave: int
        match: Optional[str] = None

        @property
        def label(self) -> str:
            error_suffix = "_error" if isinstance(self.expected, type) and issubclass(self.expected, Exception) else ""
            return f"rate_{self.sample_rate}_cutoff_{self.cutoff}_bpo_{self.bins_per_octave}{error_suffix}"

    test_cases = [
        TestCase(
            sample_rate=44100,
            cutoff=55.0,
            bins_per_octave=12,
            expected=103,
        ),
        TestCase(
            sample_rate=48000,
            cutoff=27.5,
            bins_per_octave=24,
            expected=234,
        ),
        TestCase(
            sample_rate=22050,
            cutoff=110.0,
            bins_per_octave=36,
            expected=239,
        ),
        TestCase(
            sample_rate=16000,
            cutoff=100.0,
            bins_per_octave=12,
            expected=75,
        ),
        TestCase(
            sample_rate=8000,
            cutoff=200.0,
            bins_per_octave=48,
            expected=207,
        ),
        TestCase(
            sample_rate=44100,
            cutoff=np.ceil(44100 / 2.0),
            bins_per_octave=12,
            expected=ValueError,
            match="must be less than Nyquist frequency",
        ),
        TestCase(
            sample_rate=44100,
            cutoff=44100 / 2.0 + 1000.0,
            bins_per_octave=12,
            expected=ValueError,
            match="must be less than Nyquist frequency",
        ),
        TestCase(
            sample_rate=8000,
            cutoff=np.ceil(8000 / 2.0) - 0.001,
            bins_per_octave=12,
            expected=ValueError,
            match="number of bins is not positive",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_calculate_n_bins(self, test_case: TestCase) -> None:
        if not expect_error(
            calculate_n_bins,
            test_case.expected,
            test_case.sample_rate,
            test_case.cutoff,
            test_case.bins_per_octave,
            match=test_case.match,
        ):
            result = calculate_n_bins(
                test_case.sample_rate,
                test_case.cutoff,
                test_case.bins_per_octave,
            )
            assert result == test_case.expected
            assert isinstance(result, int)


class TestToResolutionFlooredLogBands(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Union[None, Type[Exception]]
        bands: Any
        cutoff: float
        bins_per_octave: int
        match: Optional[str] = None

        @property
        def label(self) -> str:
            error_suffix = "_error" if isinstance(self.expected, type) and issubclass(self.expected, Exception) else ""
            dtype_str = self.bands.dtype if hasattr(self.bands, "dtype") else type(self.bands).__name__
            return f"dtype_{dtype_str}_cutoff_{self.cutoff}_bpo_{self.bins_per_octave}{error_suffix}"

    test_cases = [
        TestCase(
            bands=np.linspace(0.0, 22050.0, 809, dtype=np.float32),
            cutoff=54.6,
            bins_per_octave=12,
            expected=None,
        ),
        TestCase(
            bands=np.linspace(0.0, 22050.0, 809, dtype=np.float64),
            cutoff=440.0,
            bins_per_octave=24,
            expected=None,
        ),
        TestCase(
            bands=np.array([10.0, 20.0, 30.0, 40.0, 50.0], dtype=np.float64),
            cutoff=5.0,
            bins_per_octave=12,
            expected=None,
        ),
        TestCase(
            bands=[100.0, 200.0, 300.0],
            cutoff=50.0,
            bins_per_octave=12,
            expected=TypeError,
            match="must be an Array",
        ),
        TestCase(
            bands=np.array([100.0], dtype=np.float32),
            cutoff=50.0,
            bins_per_octave=12,
            expected=ValueError,
            match="at least two elements",
        ),
        TestCase(
            bands=np.array([], dtype=np.float64),
            cutoff=50.0,
            bins_per_octave=12,
            expected=ValueError,
            match="at least two elements",
        ),
        TestCase(
            bands=np.array([[100.0, 200.0], [300.0, 400.0]], dtype=np.float32),
            cutoff=50.0,
            bins_per_octave=12,
            expected=ValueError,
            match="one-dimensional",
        ),
        TestCase(
            bands=np.array([100.0, 200.0], dtype=np.float64),
            cutoff=50.0,
            bins_per_octave=0,
            expected=ValueError,
            match="positive integer",
        ),
        TestCase(
            bands=np.array([100.0, 200.0], dtype=np.float32),
            cutoff=50.0,
            bins_per_octave=-5,
            expected=ValueError,
            match="positive integer",
        ),
        TestCase(
            bands=np.array([100.0, 200.0, 300.0], dtype=np.float64),
            cutoff=300.0,
            bins_per_octave=12,
            expected=ValueError,
            match="must be less than the maximum band frequency",
        ),
        TestCase(
            bands=np.array([100.0, 200.0, 300.0], dtype=np.float32),
            cutoff=400.0,
            bins_per_octave=12,
            expected=ValueError,
            match="must be less than the maximum band frequency",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_to_resolution_floored_log_bands(self, test_case: TestCase) -> None:
        if expect_error(
            to_resolution_floored_log_bands,
            test_case.expected,
            test_case.bands,
            test_case.cutoff,
            test_case.bins_per_octave,
            match=test_case.match,
        ):
            return

        result = to_resolution_floored_log_bands(test_case.bands, test_case.cutoff, test_case.bins_per_octave)
        widths = np.diff(result)
        resolution = float(test_case.bands[1] - test_case.bands[0])
        ratio = 2.0 ** (1.0 / test_case.bins_per_octave)

        assert result[0] == pytest.approx(test_case.cutoff)
        assert result[-1] == pytest.approx(float(test_case.bands[-1]))
        assert bool(np.all(widths > 0.0))
        assert bool(np.all(widths[:-1] >= resolution * (1.0 - 1e-5)))

        logarithmic = widths[:-1] > resolution * (1.0 + 1e-3)
        if logarithmic.any():
            ratios = np.asarray(result[1:-1])[logarithmic] / np.asarray(result[:-2])[logarithmic]
            assert np.allclose(ratios, ratio, rtol=1e-3)
