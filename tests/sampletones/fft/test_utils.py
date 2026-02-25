from dataclasses import dataclass
from typing import Any, Optional, Tuple, Type, Union

import numpy as np
import pytest

from sampletones.fft.utils import calculate_n_bins, rectangle_window, to_log_even_bands
from tests.sampletones.errors import expect_error
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase, BaseRegularTestCase
from tests.suite.parametrize import parametrized


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
            result = calculate_n_bins(test_case.sample_rate, test_case.cutoff, test_case.bins_per_octave)
            assert result == test_case.expected
            assert isinstance(result, int)


class TestRectangleWindow(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        length: int

        @property
        def label(self) -> str:
            return f"length_{self.length}"

    test_cases = [
        TestCase(length=1),
        TestCase(length=10),
        TestCase(length=128),
        TestCase(length=1024),
        TestCase(length=4096),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_rectangle_window(self, test_case: TestCase) -> None:
        result = rectangle_window(test_case.length)
        assert result.shape == (test_case.length,)
        assert result.dtype == np.dtype(np.float32)
        assert np.all(result == 1.0)


class TestToLogEvenBands(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Union[Tuple[int], Type[Exception]]
        bands: Any
        cutoff: float
        n_bins: Optional[int]
        match: Optional[str] = None

        @property
        def label(self) -> str:
            error_suffix = "_error" if isinstance(self.expected, type) and issubclass(self.expected, Exception) else ""
            dtype_str = self.bands.dtype if hasattr(self.bands, "dtype") else type(self.bands).__name__
            return f"dtype_{dtype_str}_cutoff_{self.cutoff}_nbins_{self.n_bins}{error_suffix}"

    test_cases = [
        TestCase(
            bands=np.array([100.0, 200.0, 400.0, 800.0], dtype=np.float32),
            cutoff=50.0,
            n_bins=None,
            expected=(4,),
        ),
        TestCase(
            bands=np.array([100.0, 200.0, 400.0, 800.0], dtype=np.float64),
            cutoff=50.0,
            n_bins=10,
            expected=(11,),
        ),
        TestCase(
            bands=np.array([50.0, 100.0], dtype=np.float32),
            cutoff=25.0,
            n_bins=5,
            expected=(6,),
        ),
        TestCase(
            bands=np.array([10.0, 20.0, 30.0, 40.0, 50.0], dtype=np.float64),
            cutoff=5.0,
            n_bins=None,
            expected=(5,),
        ),
        TestCase(
            bands=np.array([1000.0, 2000.0, 4000.0], dtype=np.float32),
            cutoff=500.0,
            n_bins=20,
            expected=(21,),
        ),
        TestCase(
            bands=[100.0, 200.0, 300.0],
            cutoff=50.0,
            n_bins=None,
            expected=TypeError,
            match="must be an Array",
        ),
        TestCase(
            bands=np.array([100.0], dtype=np.float32),
            cutoff=50.0,
            n_bins=None,
            expected=ValueError,
            match="at least two elements",
        ),
        TestCase(
            bands=np.array([], dtype=np.float64),
            cutoff=50.0,
            n_bins=None,
            expected=ValueError,
            match="at least two elements",
        ),
        TestCase(
            bands=np.array([[100.0, 200.0], [300.0, 400.0]], dtype=np.float32),
            cutoff=50.0,
            n_bins=None,
            expected=ValueError,
            match="one-dimensional",
        ),
        TestCase(
            bands=np.array([100.0, 200.0], dtype=np.float64),
            cutoff=50.0,
            n_bins=0,
            expected=ValueError,
            match="positive integer",
        ),
        TestCase(
            bands=np.array([100.0, 200.0], dtype=np.float32),
            cutoff=50.0,
            n_bins=-5,
            expected=ValueError,
            match="positive integer",
        ),
        TestCase(
            bands=np.array([100.0, 200.0, 300.0], dtype=np.float64),
            cutoff=300.0,
            n_bins=None,
            expected=ValueError,
            match="must be less than the maximum band frequency",
        ),
        TestCase(
            bands=np.array([100.0, 200.0, 300.0], dtype=np.float32),
            cutoff=400.0,
            n_bins=None,
            expected=ValueError,
            match="must be less than the maximum band frequency",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_to_log_even_bands(self, test_case: TestCase) -> None:
        if not expect_error(
            to_log_even_bands,
            test_case.expected,
            test_case.bands,
            test_case.cutoff,
            test_case.n_bins,
            match=test_case.match,
        ):
            result = to_log_even_bands(test_case.bands, test_case.cutoff, test_case.n_bins)
            assert result.shape == test_case.expected
            assert result[0] == pytest.approx(test_case.cutoff)
            assert result[-1] == pytest.approx(test_case.bands[-1])

            log_result = np.log(result)
            diffs = np.diff(log_result)
            assert np.allclose(diffs, diffs[0])
