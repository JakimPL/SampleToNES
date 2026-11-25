from dataclasses import dataclass
from typing import Any, Final, Optional, Tuple, Type, Union

import numpy as np
import pytest

from sampletones_core.constants.spectrum import BINS_PER_OCTAVE, LOG_FFT_CUTOFF_FREQUENCY
from sampletones_core.fft.fft import calculate_fft_bin_edges
from sampletones_core.fft.utils import (
    calculate_n_bins,
    to_resolution_floored_log_bands,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase, BaseRegularTestCase
from tests.suite.errors import expect_error

LOG_BANDS_SAMPLE_RATE: Final[int] = 44100
STEP_RATIO: Final[float] = 2.0 ** (1.0 / BINS_PER_OCTAVE)
WIDTH_TOLERANCE: Final[float] = 1e-3
STEP_TOLERANCE: Final[float] = 1e-5


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

    test_cases = (
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
    )

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

    test_cases = (
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
    )

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

        assert bool(np.isin(result[0], test_case.bands))
        assert result[0] <= max(test_case.cutoff, float(test_case.bands[0])) < result[1]
        assert result[-1] == pytest.approx(float(test_case.bands[-1]))
        assert bool(np.all(widths > 0.0))
        assert bool(np.all(widths[:-1] >= resolution * (1.0 - 1e-5)))

        logarithmic = widths[:-1] > resolution * (1.0 + 1e-3)
        if logarithmic.any():
            ratios = np.asarray(result[1:-1])[logarithmic] / np.asarray(result[:-2])[logarithmic]
            assert np.allclose(ratios, ratio, rtol=1e-3)


class TestTheFlooredRegionReadsTheSourceEdges(BaseTestSuite):
    """
    Up to where a logarithmic step outgrows the source spacing, every log edge is a source edge, so each
    band there is one whole source band. The source edges are the FFT's own at several sizes, cast as the
    spectrum casts them, and the same edges offset by half a band.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        size: int
        offset: float

        @property
        def spacing(self) -> float:
            return LOG_BANDS_SAMPLE_RATE / self.size

        @property
        def bands(self) -> np.ndarray:
            edges = calculate_fft_bin_edges(self.size, LOG_BANDS_SAMPLE_RATE) + self.offset * self.spacing
            return edges.astype(np.float32)

        @property
        def turning_frequency(self) -> float:
            """The frequency where a logarithmic step is as wide as the source spacing."""
            return self.spacing / (STEP_RATIO - 1.0)

    test_cases = (
        TestCase(label="fft size 1615", size=1615, offset=0.0),
        TestCase(label="fft size 1616", size=1616, offset=0.0),
        TestCase(label="fft size 2048", size=2048, offset=0.0),
        TestCase(label="fft size 1615 offset by half a band", size=1615, offset=-0.5),
        TestCase(label="fft size 2048 offset by half a band", size=2048, offset=-0.5),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_edges_below_the_turn_are_the_source_edges(self, test_case: TestCase) -> None:
        bands = test_case.bands

        result = to_resolution_floored_log_bands(bands, LOG_FFT_CUTOFF_FREQUENCY, BINS_PER_OCTAVE)

        floored = result[result <= test_case.turning_frequency]
        source = bands[(bands >= result[0]) & (bands <= test_case.turning_frequency)]
        assert np.array_equal(floored, source)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_axis_starts_with_the_source_band_holding_the_cutoff(self, test_case: TestCase) -> None:
        bands = test_case.bands

        result = to_resolution_floored_log_bands(bands, LOG_FFT_CUTOFF_FREQUENCY, BINS_PER_OCTAVE)

        assert bool(np.isin(result[0], bands))
        assert result[0] <= LOG_FFT_CUTOFF_FREQUENCY < result[1]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_axis_turns_logarithmic_at_the_first_source_edge_past_the_turning_frequency(
        self, test_case: TestCase
    ) -> None:
        bands = test_case.bands

        result = np.asarray(to_resolution_floored_log_bands(bands, LOG_FFT_CUTOFF_FREQUENCY, BINS_PER_OCTAVE))

        edges = result.astype(np.float64)
        widths = np.diff(edges)
        turning = int(np.argmax(widths > test_case.spacing * (1.0 + WIDTH_TOLERANCE)))
        assert bool(np.isin(result[turning], bands))
        assert test_case.turning_frequency < edges[turning] <= test_case.turning_frequency + test_case.spacing
        assert np.allclose(edges[turning + 1 : -1] / edges[turning:-2], STEP_RATIO, rtol=STEP_TOLERANCE)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_bands_rise_strictly_to_the_top_source_edge(self, test_case: TestCase) -> None:
        bands = test_case.bands

        result = to_resolution_floored_log_bands(bands, LOG_FFT_CUTOFF_FREQUENCY, BINS_PER_OCTAVE)

        assert result.dtype == bands.dtype
        assert bool(np.all(np.diff(result) > 0.0))
        assert result[-1] == bands[-1]


class TestTheAxisRunsFromTheCutoffsSourceEdge(BaseTestSuite):
    """
    The axis starts at the source edge at or below the cutoff, or at the lowest one when the cutoff lies
    below every source edge. It keeps the source edges while a logarithmic step fits within the source band
    above, then steps by the logarithmic factor to the top source edge.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        bands: Tuple[float, ...]
        cutoff: float
        bins_per_octave: int
        expected: Tuple[float, ...]

    test_cases = (
        TestCase(
            label="cutoff between source edges",
            bands=(10.0, 20.0, 30.0, 40.0, 50.0),
            cutoff=25.0,
            bins_per_octave=12,
            expected=(20.0, 30.0, 40.0, 50.0),
        ),
        TestCase(
            label="cutoff on a source edge",
            bands=(10.0, 20.0, 30.0, 40.0, 50.0),
            cutoff=30.0,
            bins_per_octave=12,
            expected=(30.0, 40.0, 50.0),
        ),
        TestCase(
            label="cutoff below every source edge",
            bands=(10.0, 20.0, 30.0, 40.0, 50.0),
            cutoff=5.0,
            bins_per_octave=12,
            expected=(10.0, 20.0, 30.0, 40.0, 50.0),
        ),
        TestCase(
            label="a step as wide as its source band keeps the source edge",
            bands=(10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0),
            cutoff=10.0,
            bins_per_octave=1,
            expected=(10.0, 20.0, 40.0, 80.0, 90.0),
        ),
        TestCase(
            label="the first step outgrows its source band",
            bands=(100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0, 180.0, 190.0, 200.0, 210.0),
            cutoff=100.0,
            bins_per_octave=1,
            expected=(100.0, 200.0, 210.0),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_axis_edges(self, test_case: TestCase) -> None:
        bands = np.asarray(test_case.bands, dtype=np.float64)

        result = to_resolution_floored_log_bands(bands, test_case.cutoff, test_case.bins_per_octave)

        assert np.array_equal(result, np.asarray(test_case.expected))
