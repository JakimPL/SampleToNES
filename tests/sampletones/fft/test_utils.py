from dataclasses import dataclass
from typing import Any, Optional, Tuple, Type, Union

import numpy as np
import pytest

from sampletones.fft.utils import calculate_n_bins, rectangle_window, to_log_even_bands
from tests.sampletones.errors import expect_error


class TestCalculateNBins:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        sample_rate: int
        cutoff: float
        bins_per_octave: int
        expected_result: Union[int, Type[Exception]]
        match: Optional[str] = None

        @property
        def test_id(self) -> str:
            error_suffix = (
                "_error"
                if isinstance(self.expected_result, type) and issubclass(self.expected_result, Exception)
                else ""
            )
            return f"rate_{self.sample_rate}_cutoff_{self.cutoff}_bpo_{self.bins_per_octave}{error_suffix}"

    test_cases = [
        TestCase(
            sample_rate=44100,
            cutoff=55.0,
            bins_per_octave=12,
            expected_result=103,
        ),
        TestCase(
            sample_rate=48000,
            cutoff=27.5,
            bins_per_octave=24,
            expected_result=234,
        ),
        TestCase(
            sample_rate=22050,
            cutoff=110.0,
            bins_per_octave=36,
            expected_result=239,
        ),
        TestCase(
            sample_rate=16000,
            cutoff=100.0,
            bins_per_octave=12,
            expected_result=75,
        ),
        TestCase(
            sample_rate=8000,
            cutoff=200.0,
            bins_per_octave=48,
            expected_result=207,
        ),
        TestCase(
            sample_rate=44100,
            cutoff=np.ceil(44100 / 2.0),
            bins_per_octave=12,
            expected_result=ValueError,
            match="must be less than Nyquist frequency",
        ),
        TestCase(
            sample_rate=44100,
            cutoff=44100 / 2.0 + 1000.0,
            bins_per_octave=12,
            expected_result=ValueError,
            match="must be less than Nyquist frequency",
        ),
        TestCase(
            sample_rate=8000,
            cutoff=np.ceil(8000 / 2.0) - 0.001,
            bins_per_octave=12,
            expected_result=ValueError,
            match="number of bins is not positive",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_calculate_n_bins(self, test_case: TestCase) -> None:
        if not expect_error(
            calculate_n_bins,
            test_case.expected_result,
            test_case.sample_rate,
            test_case.cutoff,
            test_case.bins_per_octave,
            match=test_case.match,
        ):
            result = calculate_n_bins(test_case.sample_rate, test_case.cutoff, test_case.bins_per_octave)
            assert result == test_case.expected_result
            assert isinstance(result, int)


class TestRectangleWindow:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        length: int

        @property
        def test_id(self) -> str:
            return f"length_{self.length}"

    test_cases = [
        TestCase(length=1),
        TestCase(length=10),
        TestCase(length=128),
        TestCase(length=1024),
        TestCase(length=4096),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_rectangle_window(self, test_case: TestCase) -> None:
        result = rectangle_window(test_case.length)
        assert result.shape == (test_case.length,)
        assert result.dtype == np.dtype(np.float32)
        assert np.all(result == 1.0)


class TestToLogEvenBands:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        bands: Any
        cutoff: float
        n_bins: Optional[int]
        expected_result: Union[Tuple[int], Type[Exception]]
        match: Optional[str] = None

        @property
        def test_id(self) -> str:
            error_suffix = (
                "_error"
                if isinstance(self.expected_result, type) and issubclass(self.expected_result, Exception)
                else ""
            )
            dtype_str = self.bands.dtype if hasattr(self.bands, "dtype") else type(self.bands).__name__
            return f"dtype_{dtype_str}_cutoff_{self.cutoff}_nbins_{self.n_bins}{error_suffix}"

    test_cases = [
        TestCase(
            bands=np.array([100.0, 200.0, 400.0, 800.0], dtype=np.float32),
            cutoff=50.0,
            n_bins=None,
            expected_result=(4,),
        ),
        TestCase(
            bands=np.array([100.0, 200.0, 400.0, 800.0], dtype=np.float64),
            cutoff=50.0,
            n_bins=10,
            expected_result=(11,),
        ),
        TestCase(
            bands=np.array([50.0, 100.0], dtype=np.float32),
            cutoff=25.0,
            n_bins=5,
            expected_result=(6,),
        ),
        TestCase(
            bands=np.array([10.0, 20.0, 30.0, 40.0, 50.0], dtype=np.float64),
            cutoff=5.0,
            n_bins=None,
            expected_result=(5,),
        ),
        TestCase(
            bands=np.array([1000.0, 2000.0, 4000.0], dtype=np.float32),
            cutoff=500.0,
            n_bins=20,
            expected_result=(21,),
        ),
        TestCase(
            bands=[100.0, 200.0, 300.0],
            cutoff=50.0,
            n_bins=None,
            expected_result=TypeError,
            match="must be an Array",
        ),
        TestCase(
            bands=np.array([100.0], dtype=np.float32),
            cutoff=50.0,
            n_bins=None,
            expected_result=ValueError,
            match="at least two elements",
        ),
        TestCase(
            bands=np.array([], dtype=np.float64),
            cutoff=50.0,
            n_bins=None,
            expected_result=ValueError,
            match="at least two elements",
        ),
        TestCase(
            bands=np.array([[100.0, 200.0], [300.0, 400.0]], dtype=np.float32),
            cutoff=50.0,
            n_bins=None,
            expected_result=ValueError,
            match="one-dimensional",
        ),
        TestCase(
            bands=np.array([100.0, 200.0], dtype=np.float64),
            cutoff=50.0,
            n_bins=0,
            expected_result=ValueError,
            match="positive integer",
        ),
        TestCase(
            bands=np.array([100.0, 200.0], dtype=np.float32),
            cutoff=50.0,
            n_bins=-5,
            expected_result=ValueError,
            match="positive integer",
        ),
        TestCase(
            bands=np.array([100.0, 200.0, 300.0], dtype=np.float64),
            cutoff=300.0,
            n_bins=None,
            expected_result=ValueError,
            match="must be less than the maximum band frequency",
        ),
        TestCase(
            bands=np.array([100.0, 200.0, 300.0], dtype=np.float32),
            cutoff=400.0,
            n_bins=None,
            expected_result=ValueError,
            match="must be less than the maximum band frequency",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_to_log_even_bands(self, test_case: TestCase) -> None:
        if not expect_error(
            to_log_even_bands,
            test_case.expected_result,
            test_case.bands,
            test_case.cutoff,
            test_case.n_bins,
            match=test_case.match,
        ):
            result = to_log_even_bands(test_case.bands, test_case.cutoff, test_case.n_bins)
            assert result.shape == test_case.expected_result
            assert result[0] == pytest.approx(test_case.cutoff)
            assert result[-1] == pytest.approx(test_case.bands[-1])

            log_result = np.log(result)
            diffs = np.diff(log_result)
            assert np.allclose(diffs, diffs[0])
