from dataclasses import dataclass
from typing import Any, Optional, Tuple, Type, Union

import numpy as np
import pytest
from pydantic import ValidationError

from sampletones.structures.histogram.histogram import Histogram
from sampletones.structures.histogram.interval import Interval
from sampletones.types.array import Array, Float, Numeric
from tests.sampletones.arrays import assert_array_equal
from tests.sampletones.errors import expect_error, expect_warning


class TestInit:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        edges: Array
        values: Union[Array, Float]
        expected_result: Union[Histogram, Type[Exception]]
        match: Optional[str] = None

        @property
        def test_id(self) -> str:
            if isinstance(self.expected_result, type) and issubclass(self.expected_result, Exception):
                error_suffix = "_error"
            else:
                error_suffix = ""
            edges_dtype = self.edges.dtype.name
            values_dtype = self.values.dtype.name if isinstance(self.values, np.ndarray) else "scalar"
            return f"edges_{edges_dtype}_values_{values_dtype}{error_suffix}"

    test_cases = [
        TestCase(
            edges=np.array([0.0, 1.0, 2.0], dtype=np.float64),
            values=np.array([1.0, 2.0], dtype=np.float64),
            expected_result=Histogram(
                np.array([0.0, 1.0, 2.0], dtype=np.float64), np.array([1.0, 2.0], dtype=np.float64)
            ),
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 4.0], dtype=np.float32),
            values=np.array([2.0, 6.0], dtype=np.float32),
            expected_result=Histogram(
                np.array([0.0, 1.0, 4.0], dtype=np.float32), np.array([2.0, 6.0], dtype=np.float32)
            ),
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 2.0, 3.0], dtype=np.float32),
            values=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            expected_result=Histogram(
                np.array([0.0, 1.0, 2.0, 3.0], dtype=np.float32), np.array([1.0, 2.0, 3.0], dtype=np.float32)
            ),
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 4.0], dtype=np.float32),
            values=np.float32(3.0),
            expected_result=Histogram(
                np.array([0.0, 1.0, 4.0], dtype=np.float32), np.array([3.0, 9.0], dtype=np.float32)
            ),
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 4.0], dtype=np.float64),
            values=np.float64(3.0),
            expected_result=Histogram(
                np.array([0.0, 1.0, 4.0], dtype=np.float64), np.array([3.0, 9.0], dtype=np.float64)
            ),
        ),
        TestCase(
            edges=np.array([0, 1, 2], dtype=np.int64),
            values=np.array([1, 2], dtype=np.int64),
            expected_result=Histogram(np.array([0, 1, 2], dtype=np.int64), np.array([1, 2], dtype=np.int64)),
        ),
        TestCase(
            edges=np.array([0, 1, 4], dtype=np.int32),
            values=np.array([2, 6], dtype=np.int32),
            expected_result=Histogram(np.array([0, 1, 4], dtype=np.int32), np.array([2, 6], dtype=np.int32)),
        ),
        TestCase(
            edges=np.array([0.0, 1.0, np.inf], dtype=np.float32),
            values=np.array([1.0, 2.0], dtype=np.float32),
            expected_result=ValidationError,
        ),
        TestCase(
            edges=np.array([-np.inf, 0.0, np.inf], dtype=np.float64),
            values=np.array([1.0, 2.0], dtype=np.float64),
            expected_result=ValidationError,
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 2.0], dtype=np.float32),
            values=np.array([np.nan, 2.0], dtype=np.float32),
            expected_result=Histogram(
                np.array([0.0, 1.0, 2.0], dtype=np.float32), np.array([np.nan, 2.0], dtype=np.float32)
            ),
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 2.0], dtype=np.float64),
            values=np.array([1.0], dtype=np.float64),
            expected_result=ValueError,
            match="edges should have exactly",
        ),
        TestCase(
            edges=np.array([0.0, 1.0], dtype=np.float32),
            values=np.array([1.0, 2.0], dtype=np.float32),
            expected_result=ValueError,
            match="edges should have exactly",
        ),
        TestCase(
            edges=np.array([0.0], dtype=np.float64),
            values=np.array([], dtype=np.float64),
            expected_result=ValueError,
            match="At least two edges",
        ),
        TestCase(
            edges=np.array([2.0, 1.0, 3.0], dtype=np.float32),
            values=np.array([1.0, 2.0], dtype=np.float32),
            expected_result=ValueError,
            match="strictly increasing",
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 1.0, 2.0], dtype=np.float64),
            values=np.array([1.0, 2.0, 3.0], dtype=np.float64),
            expected_result=ValueError,
            match="strictly increasing",
        ),
        TestCase(
            edges=np.array([0, 1, 0], dtype=np.int32),
            values=np.array([1, 2], dtype=np.int32),
            expected_result=ValueError,
            match="strictly increasing",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_init(self, test_case: TestCase) -> None:
        if not expect_error(
            Histogram, test_case.expected_result, test_case.edges, test_case.values, match=test_case.match
        ):
            assert isinstance(test_case.expected_result, Histogram)
            histogram = Histogram(test_case.edges, test_case.values)
            assert_array_equal(histogram.values, test_case.expected_result.values)
            assert_array_equal(histogram.edges, test_case.expected_result.edges)
            assert histogram.edges.dtype == test_case.expected_result.edges.dtype
            assert histogram.values.dtype == test_case.expected_result.values.dtype


class TestImmutability:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        edges: Array
        values: Array

        @property
        def test_id(self) -> str:
            return f"{self.edges.dtype.name}"

    test_cases = [
        TestCase(
            edges=np.array([0.0, 1.0, 4.0], dtype=np.float64),
            values=np.array([1.0, 2.0], dtype=np.float64),
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 4.0], dtype=np.float32),
            values=np.array([1.0, 2.0], dtype=np.float32),
        ),
        TestCase(
            edges=np.array([1, 2, 3], dtype=np.int64),
            values=np.array([1, 2], dtype=np.int64),
        ),
        TestCase(
            edges=np.array([42, 137, 404], dtype=np.int32),
            values=np.array([1, 2], dtype=np.int32),
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_immutability(self, test_case: TestCase) -> None:
        histogram = Histogram(test_case.edges, test_case.values)

        with pytest.raises(ValueError):
            histogram.edges[0] = 5.0

        with pytest.raises(ValueError):
            histogram.values[0] = 5.0

        with pytest.raises(ValidationError):
            histogram.edges = np.array([0.0, 1.0, 3.0])

        with pytest.raises(ValidationError):
            histogram.values = np.array([2.0, 3.0])


class TestInitConstantDensity:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        edges: Array
        density: Float
        expected_values: Array
        expected_densities: Array

        @property
        def test_id(self) -> str:
            return f"{self.edges.dtype.name}"

    test_cases = [
        TestCase(
            edges=np.array([0.0, 1.0, 4.0], dtype=np.float64),
            density=3.0,
            expected_values=np.array([3.0, 9.0]),
            expected_densities=np.array([3.0, 3.0]),
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 4.0], dtype=np.float32),
            density=np.float32(3.0),
            expected_values=np.array([3.0, 9.0], dtype=np.float32),
            expected_densities=np.array([3.0, 3.0], dtype=np.float32),
        ),
        TestCase(
            edges=np.array([0, 1, 4], dtype=np.int64),
            density=3,
            expected_values=np.array([3, 9], dtype=np.int64),
            expected_densities=np.array([3.0, 3.0]),
        ),
        TestCase(
            edges=np.array([0, 1, 4], dtype=np.int32),
            density=3.0,
            expected_values=np.array([3, 9], dtype=np.int32),
            expected_densities=np.array([3.0, 3.0]),
        ),
        TestCase(
            edges=np.array([0.0, 2.0, 3.0, 8.0], dtype=np.float64),
            density=2.5,
            expected_values=np.array([5.0, 2.5, 12.5]),
            expected_densities=np.array([2.5, 2.5, 2.5]),
        ),
        TestCase(
            edges=np.array([0.0, 0.5, 2.0, 3.0], dtype=np.float32),
            density=np.float32(4.0),
            expected_values=np.array([2.0, 6.0, 4.0], dtype=np.float32),
            expected_densities=np.array([4.0, 4.0, 4.0], dtype=np.float32),
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_constant_density(self, test_case: TestCase) -> None:
        histogram = Histogram(test_case.edges, test_case.density)
        np.testing.assert_array_equal(histogram.values, test_case.expected_values)
        np.testing.assert_array_equal(histogram.densities, test_case.expected_densities)


class TestEquality:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        histogram1: Any
        histogram2: Any
        expected_equal: bool
        description: str

        @property
        def test_id(self) -> str:
            return self.description

    test_cases = [
        TestCase(
            histogram1=Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float64), np.array([1.0, 2.0], dtype=np.float64)),
            histogram2=Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float64), np.array([1.0, 2.0], dtype=np.float64)),
            expected_equal=True,
            description="equal_float64",
        ),
        TestCase(
            histogram1=Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float32), np.array([1.0, 2.0], dtype=np.float32)),
            histogram2=Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float32), np.array([1.0, 2.0], dtype=np.float32)),
            expected_equal=True,
            description="equal_float32",
        ),
        TestCase(
            histogram1=Histogram(np.array([0, 1, 2], dtype=np.int64), np.array([1, 2], dtype=np.int64)),
            histogram2=Histogram(np.array([0, 1, 2], dtype=np.int64), np.array([1, 2], dtype=np.int64)),
            expected_equal=True,
            description="equal_int64",
        ),
        TestCase(
            histogram1=Histogram(np.array([0, 1, 2], dtype=np.int32), np.array([1, 2], dtype=np.int32)),
            histogram2=Histogram(np.array([0, 1, 2], dtype=np.int32), np.array([1, 2], dtype=np.int32)),
            expected_equal=True,
            description="equal_int32",
        ),
        TestCase(
            histogram1=Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float64), np.array([1.0, 2.0], dtype=np.float64)),
            histogram2=Histogram(np.array([0.0, 1.0, 3.0], dtype=np.float64), np.array([1.0, 2.0], dtype=np.float64)),
            expected_equal=False,
            description="different_edges",
        ),
        TestCase(
            histogram1=Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float64), np.array([1.0, 2.0], dtype=np.float64)),
            histogram2=Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float64), np.array([1.0, 3.0], dtype=np.float64)),
            expected_equal=False,
            description="different_values",
        ),
        TestCase(
            histogram1=Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float32), np.array([1.0, 2.0], dtype=np.float32)),
            histogram2=Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float64), np.array([1.0, 2.0], dtype=np.float64)),
            expected_equal=True,
            description="float32_vs_float64",
        ),
        TestCase(
            histogram1=Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float64), np.array([1.0, 2.0], dtype=np.float64)),
            histogram2=Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float32), np.array([1.0, 2.0], dtype=np.float32)),
            expected_equal=True,
            description="float64_vs_float32",
        ),
        TestCase(
            histogram1=Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float32), np.array([1.0, 2.0], dtype=np.float32)),
            histogram2=Histogram(np.array([0, 1, 2], dtype=np.int64), np.array([1, 2], dtype=np.int64)),
            expected_equal=True,
            description="float32_vs_int64",
        ),
        TestCase(
            histogram1=Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float64), np.array([1.0, 2.0], dtype=np.float64)),
            histogram2=Histogram(np.array([0, 1, 2], dtype=np.int32), np.array([1, 2], dtype=np.int32)),
            expected_equal=True,
            description="float64_vs_int32",
        ),
        TestCase(
            histogram1=Histogram(np.array([0, 1, 2], dtype=np.int64), np.array([1, 2], dtype=np.int64)),
            histogram2=Histogram(np.array([0, 1, 2], dtype=np.int32), np.array([1, 2], dtype=np.int32)),
            expected_equal=True,
            description="int64_vs_int32",
        ),
        TestCase(
            histogram1=Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
            histogram2="not a histogram",
            expected_equal=False,
            description="histogram_vs_string",
        ),
        TestCase(
            histogram1=Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
            histogram2=42,
            expected_equal=False,
            description="histogram_vs_int",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_equality(self, test_case: TestCase) -> None:
        if test_case.expected_equal:
            assert test_case.histogram1 == test_case.histogram2
        else:
            assert test_case.histogram1 != test_case.histogram2


class TestCopy:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        histogram: Histogram

        @property
        def test_id(self) -> str:
            return f"{self.histogram.edges.dtype.name}"

    test_cases = [
        TestCase(
            histogram=Histogram(
                np.array([0.0, 1.0, 2.0], dtype=np.float64),
                np.array([1.0, 2.0], dtype=np.float64),
            ),
        ),
        TestCase(
            histogram=Histogram(
                np.array([0.0, 1.0, 2.0], dtype=np.float32),
                np.array([1.0, 2.0], dtype=np.float32),
            ),
        ),
        TestCase(
            histogram=Histogram(
                np.array([0, 1, 2], dtype=np.int64),
                np.array([1, 2], dtype=np.int64),
            ),
        ),
        TestCase(
            histogram=Histogram(
                np.array([0, 1, 2], dtype=np.int32),
                np.array([1, 2], dtype=np.int32),
            ),
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_copy(self, test_case: TestCase) -> None:
        copied = test_case.histogram.__copy__()
        assert copied == test_case.histogram
        assert copied is not test_case.histogram

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_deepcopy(self, test_case: TestCase) -> None:
        copied = test_case.histogram.__deepcopy__()
        assert copied == test_case.histogram
        assert copied is not test_case.histogram
        assert copied.edges is not test_case.histogram.edges
        assert copied.values is not test_case.histogram.values


class TestHash:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        histogram: Histogram

        @property
        def test_id(self) -> str:
            return f"{self.histogram.edges.dtype.name}"

    test_cases = [
        TestCase(
            histogram=Histogram(
                np.array([0.0, 1.0, 2.0], dtype=np.float64),
                np.array([1.0, 2.0], dtype=np.float64),
            ),
        ),
        TestCase(
            histogram=Histogram(
                np.array([0.0, 1.0, 2.0], dtype=np.float32),
                np.array([1.0, 2.0], dtype=np.float32),
            ),
        ),
        TestCase(
            histogram=Histogram(
                np.array([0, 1, 2], dtype=np.int64),
                np.array([1, 2], dtype=np.int64),
            ),
        ),
        TestCase(
            histogram=Histogram(
                np.array([0, 1, 2], dtype=np.int32),
                np.array([1, 2], dtype=np.int32),
            ),
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_hash_equal_histograms(self, test_case: TestCase) -> None:
        histogram2 = Histogram(test_case.histogram.edges.copy(), test_case.histogram.values.copy())
        assert hash(test_case.histogram) == hash(histogram2)

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_hash_different_histograms(self, test_case: TestCase) -> None:
        different_values = test_case.histogram.values.copy()
        different_values[-1] = different_values[-1] + 1
        histogram2 = Histogram(test_case.histogram.edges, different_values)
        assert hash(test_case.histogram) != hash(histogram2)


class TestLen:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        histogram: Histogram
        expected_length: int

        @property
        def test_id(self) -> str:
            return f"{self.histogram.edges.dtype.name}_len_{self.expected_length}"

    test_cases = [
        TestCase(
            histogram=Histogram(
                np.array([0.0, 1.0, 2.0, 3.0], dtype=np.float64),
                np.array([1.0, 2.0, 3.0], dtype=np.float64),
            ),
            expected_length=3,
        ),
        TestCase(
            histogram=Histogram(
                np.array([0.0, 1.0], dtype=np.float32),
                np.array([5.0], dtype=np.float32),
            ),
            expected_length=1,
        ),
        TestCase(
            histogram=Histogram(
                np.array([0, 1, 2, 3, 4], dtype=np.int64),
                np.array([1, 2, 3, 4], dtype=np.int64),
            ),
            expected_length=4,
        ),
        TestCase(
            histogram=Histogram(
                np.array([0, 1, 2], dtype=np.int32),
                np.array([5, 10], dtype=np.int32),
            ),
            expected_length=2,
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_len(self, test_case: TestCase) -> None:
        assert len(test_case.histogram) == test_case.expected_length


class TestInterval:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        histogram: Histogram
        index: int
        expected_result: Union[Interval, Type[Exception]]
        match: Optional[str] = None

        @property
        def test_id(self) -> str:
            dtype = self.histogram.edges.dtype.name
            base = f"{dtype}_index_{self.index}"
            if isinstance(self.expected_result, type) and issubclass(self.expected_result, Exception):
                return f"{base}_error"

            return base

    test_cases = [
        TestCase(
            histogram=Histogram(
                np.array([0.0, 1.0, 3.0], dtype=np.float64),
                np.array([1.0, 2.0], dtype=np.float64),
            ),
            index=0,
            expected_result=Interval(0.0, 1.0),
        ),
        TestCase(
            histogram=Histogram(
                np.array([0.0, 1.0, 3.0], dtype=np.float32),
                np.array([1.0, 2.0], dtype=np.float32),
            ),
            index=1,
            expected_result=Interval(1.0, 3.0),
        ),
        TestCase(
            histogram=Histogram(
                np.array([0, 1, 4], dtype=np.int64),
                np.array([2, 6], dtype=np.int64),
            ),
            index=0,
            expected_result=Interval(0, 1),
        ),
        TestCase(
            histogram=Histogram(
                np.array([0, 5, 10], dtype=np.int32),
                np.array([10, 15], dtype=np.int32),
            ),
            index=1,
            expected_result=Interval(5, 10),
        ),
        TestCase(
            histogram=Histogram(
                np.array([0.0, 1.0, 2.0], dtype=np.float64),
                np.array([1.0, 2.0], dtype=np.float64),
            ),
            index=-1,
            expected_result=Interval(1.0, 2.0),
        ),
        TestCase(
            histogram=Histogram(
                np.array([0.0, 1.0, 2.0], dtype=np.float32),
                np.array([1.0, 2.0], dtype=np.float32),
            ),
            index=-2,
            expected_result=Interval(0.0, 1.0),
        ),
        TestCase(
            histogram=Histogram(
                np.array([0, 1, 4], dtype=np.int64),
                np.array([2, 6], dtype=np.int64),
            ),
            index=-1,
            expected_result=Interval(1, 4),
        ),
        TestCase(
            histogram=Histogram(
                np.array([0, 5, 10], dtype=np.int32),
                np.array([10, 15], dtype=np.int32),
            ),
            index=-2,
            expected_result=Interval(0, 5),
        ),
        TestCase(
            histogram=Histogram(
                np.array([0.0, 1.0, 2.0], dtype=np.float64),
                np.array([1.0, 2.0], dtype=np.float64),
            ),
            index=2,
            expected_result=IndexError,
            match="out of bounds",
        ),
        TestCase(
            histogram=Histogram(
                np.array([0, 1, 2], dtype=np.int64),
                np.array([1, 2], dtype=np.int64),
            ),
            index=5,
            expected_result=IndexError,
            match="out of bounds",
        ),
        TestCase(
            histogram=Histogram(
                np.array([0, 1, 2], dtype=np.int32),
                np.array([1, 2], dtype=np.int32),
            ),
            index=-3,
            expected_result=IndexError,
            match="out of bounds",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_interval(self, test_case: TestCase) -> None:
        if not expect_error(
            test_case.histogram.interval, test_case.expected_result, test_case.index, match=test_case.match
        ):
            interval = test_case.histogram.interval(test_case.index)
            assert interval == test_case.expected_result


class TestWidth:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        histogram: Histogram
        index: int
        expected_result: Union[Numeric, Type[Exception]]
        match: Optional[str] = None

        @property
        def test_id(self) -> str:
            dtype = self.histogram.edges.dtype.name
            if isinstance(self.expected_result, type) and issubclass(self.expected_result, Exception):
                return f"{dtype}_index_{self.index}_error"
            return f"{dtype}_index_{self.index}"

    test_cases = [
        TestCase(
            histogram=Histogram(
                np.array([0.0, 1.0, 2.0, 3.0], dtype=np.float64), np.array([1.0, 2.0, 3.0], dtype=np.float64)
            ),
            index=0,
            expected_result=np.float64(1.0),
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 4.0], dtype=np.float32), np.array([1.0, 2.0], dtype=np.float32)),
            index=1,
            expected_result=np.float32(3.0),
        ),
        TestCase(
            histogram=Histogram(np.array([0, 1, 5], dtype=np.int64), np.array([2, 8], dtype=np.int64)),
            index=0,
            expected_result=np.int64(1),
        ),
        TestCase(
            histogram=Histogram(np.array([0, 2, 7], dtype=np.int32), np.array([4, 10], dtype=np.int32)),
            index=1,
            expected_result=np.int32(5),
        ),
        TestCase(
            histogram=Histogram(
                np.array([0.0, 1.0, 2.0, 3.0], dtype=np.float64), np.array([1.0, 2.0, 3.0], dtype=np.float64)
            ),
            index=-1,
            expected_result=np.float64(1.0),
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 4.0], dtype=np.float32), np.array([1.0, 2.0], dtype=np.float32)),
            index=-2,
            expected_result=np.float32(1.0),
        ),
        TestCase(
            histogram=Histogram(np.array([0, 1, 5], dtype=np.int64), np.array([2, 8], dtype=np.int64)),
            index=-1,
            expected_result=np.int64(4),
        ),
        TestCase(
            histogram=Histogram(np.array([0, 2, 7], dtype=np.int32), np.array([4, 10], dtype=np.int32)),
            index=-2,
            expected_result=np.int32(2),
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float64), np.array([1.0, 2.0], dtype=np.float64)),
            index=2,
            expected_result=IndexError,
            match="out of (range|bounds)",
        ),
        TestCase(
            histogram=Histogram(np.array([0, 1, 2], dtype=np.int64), np.array([1, 2], dtype=np.int64)),
            index=5,
            expected_result=IndexError,
            match="out of (range|bounds)",
        ),
        TestCase(
            histogram=Histogram(np.array([0, 1, 2], dtype=np.int32), np.array([1, 2], dtype=np.int32)),
            index=-3,
            expected_result=IndexError,
            match="out of (range|bounds)",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_width(self, test_case: TestCase) -> None:
        if not expect_error(
            test_case.histogram.width, test_case.expected_result, test_case.index, match=test_case.match
        ):
            width = test_case.histogram.width(test_case.index)
            assert width == test_case.expected_result
            assert isinstance(width, type(test_case.expected_result))
            if isinstance(test_case.expected_result, (np.floating, np.integer)):
                assert isinstance(width, (np.floating, np.integer))
                assert width.dtype == test_case.expected_result.dtype


class TestDensity:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        histogram: Histogram
        index: int
        expected_result: Union[Float, Type[Exception]]
        match: Optional[str] = None

        @property
        def test_id(self) -> str:
            dtype = self.histogram.edges.dtype.name
            base = f"{dtype}_index_{self.index}"
            if isinstance(self.expected_result, type) and issubclass(self.expected_result, Exception):
                return f"{base}_error"

            return base

    test_cases = [
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 4.0], dtype=np.float64), np.array([2.0, 6.0], dtype=np.float64)),
            index=0,
            expected_result=np.float64(2.0),
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 2.0, 5.0], dtype=np.float32), np.array([4.0, 9.0], dtype=np.float32)),
            index=1,
            expected_result=np.float32(3.0),
        ),
        TestCase(
            histogram=Histogram(np.array([0, 2, 6], dtype=np.int64), np.array([4, 12], dtype=np.int64)),
            index=0,
            expected_result=np.float64(2.0),
        ),
        TestCase(
            histogram=Histogram(np.array([0, 5, 10], dtype=np.int32), np.array([10, 15], dtype=np.int32)),
            index=1,
            expected_result=np.float64(3.0),
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 4.0], dtype=np.float64), np.array([2.0, 6.0], dtype=np.float64)),
            index=-1,
            expected_result=np.float64(2.0),
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 2.0, 5.0], dtype=np.float32), np.array([4.0, 9.0], dtype=np.float32)),
            index=-2,
            expected_result=np.float32(2.0),
        ),
        TestCase(
            histogram=Histogram(np.array([0, 2, 6], dtype=np.int64), np.array([4, 12], dtype=np.int64)),
            index=-1,
            expected_result=np.float64(3.0),
        ),
        TestCase(
            histogram=Histogram(np.array([0, 5, 10], dtype=np.int32), np.array([10, 15], dtype=np.int32)),
            index=-2,
            expected_result=np.float64(2.0),
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float64), np.array([1.0, 2.0], dtype=np.float64)),
            index=2,
            expected_result=IndexError,
            match="out of (range|bounds)",
        ),
        TestCase(
            histogram=Histogram(np.array([0, 1, 2], dtype=np.int64), np.array([1, 2], dtype=np.int64)),
            index=5,
            expected_result=IndexError,
            match="out of (range|bounds)",
        ),
        TestCase(
            histogram=Histogram(np.array([0, 1, 2], dtype=np.int32), np.array([1, 2], dtype=np.int32)),
            index=-3,
            expected_result=IndexError,
            match="out of (range|bounds)",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_density(self, test_case: TestCase) -> None:
        if not expect_error(
            test_case.histogram.density, test_case.expected_result, test_case.index, match=test_case.match
        ):
            density = test_case.histogram.density(test_case.index)
            assert density == test_case.expected_result
            assert isinstance(density, type(test_case.expected_result))
            if isinstance(test_case.expected_result, (np.floating, np.integer)):
                assert isinstance(density, (np.floating, np.integer))
                assert density.dtype == test_case.expected_result.dtype


class TestDensities:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        histogram: Histogram
        expected_result: Array

        @property
        def test_id(self) -> str:
            return f"{self.histogram.edges.dtype.name}"

    test_cases = [
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 4.0], dtype=np.float64), np.array([2.0, 6.0], dtype=np.float64)),
            expected_result=np.array([2.0, 2.0]),
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 2.0, 5.0], dtype=np.float32), np.array([4.0, 9.0], dtype=np.float32)),
            expected_result=np.array([2.0, 3.0]),
        ),
        TestCase(
            histogram=Histogram(np.array([0, 2, 6], dtype=np.int64), np.array([4, 12], dtype=np.int64)),
            expected_result=np.array([2.0, 3.0]),
        ),
        TestCase(
            histogram=Histogram(np.array([0, 5, 10], dtype=np.int32), np.array([10, 15], dtype=np.int32)),
            expected_result=np.array([2.0, 3.0]),
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_densities(self, test_case: TestCase) -> None:
        np.testing.assert_array_almost_equal(test_case.histogram.densities, test_case.expected_result)


class TestWidths:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        histogram: Histogram
        expected_result: Array

        @property
        def test_id(self) -> str:
            return f"{self.histogram.edges.dtype.name}"

    test_cases = [
        TestCase(
            histogram=Histogram(
                np.array([0.0, 1.0, 4.0, 7.0], dtype=np.float64), np.array([1.0, 2.0, 3.0], dtype=np.float64)
            ),
            expected_result=np.array([1.0, 3.0, 3.0], dtype=np.float64),
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 2.0, 5.0], dtype=np.float32), np.array([4.0, 9.0], dtype=np.float32)),
            expected_result=np.array([2.0, 3.0], dtype=np.float32),
        ),
        TestCase(
            histogram=Histogram(np.array([0, 1, 5], dtype=np.int64), np.array([2, 8], dtype=np.int64)),
            expected_result=np.array([1, 4], dtype=np.int64),
        ),
        TestCase(
            histogram=Histogram(np.array([0, 3, 10], dtype=np.int32), np.array([6, 14], dtype=np.int32)),
            expected_result=np.array([3, 7], dtype=np.int32),
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_widths(self, test_case: TestCase) -> None:
        assert_array_equal(test_case.histogram.widths, test_case.expected_result)


class TestRange:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        histogram: Histogram
        expected_result: Interval

        @property
        def test_id(self) -> str:
            return f"{self.histogram.edges.dtype.name}"

    test_cases = [
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float64), np.array([1.0, 2.0], dtype=np.float64)),
            expected_result=Interval(0.0, 2.0),
        ),
        TestCase(
            histogram=Histogram(np.array([-5.0, 0.0, 5.0], dtype=np.float32), np.array([1.0, 2.0], dtype=np.float32)),
            expected_result=Interval(-5.0, 5.0),
        ),
        TestCase(
            histogram=Histogram(np.array([0, 10, 20], dtype=np.int64), np.array([5, 10], dtype=np.int64)),
            expected_result=Interval(0, 20),
        ),
        TestCase(
            histogram=Histogram(np.array([-10, 0, 10], dtype=np.int32), np.array([5, 5], dtype=np.int32)),
            expected_result=Interval(-10, 10),
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_range(self, test_case: TestCase) -> None:
        assert test_case.histogram.range == test_case.expected_result


class TestTotal:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        histogram: Histogram
        expected_result: Float

        @property
        def test_id(self) -> str:
            return f"{self.histogram.edges.dtype.name}_{len(self.histogram.values)}bins"

    test_cases = [
        TestCase(
            histogram=Histogram(
                np.array([0.0, 1.0, 4.0, 7.0], dtype=np.float64), np.array([2.0, 6.0, 3.0], dtype=np.float64)
            ),
            expected_result=np.float64(11.0),
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 2.5, 7.0], dtype=np.float32), np.array([5.0, 10.5], dtype=np.float32)),
            expected_result=np.float32(15.5),
        ),
        TestCase(
            histogram=Histogram(np.array([0, 3, 8, 15], dtype=np.int64), np.array([6, 20, 14], dtype=np.int64)),
            expected_result=np.int64(40),
        ),
        TestCase(
            histogram=Histogram(np.array([0, 5, 12], dtype=np.int32), np.array([15, 28], dtype=np.int32)),
            expected_result=np.int32(43),
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 2.0], dtype=np.float64), np.array([7.5], dtype=np.float64)),
            expected_result=np.float64(7.5),
        ),
        TestCase(
            histogram=Histogram(np.array([-5.0, 3.5], dtype=np.float32), np.array([12.25], dtype=np.float32)),
            expected_result=np.float32(12.25),
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_total(self, test_case: TestCase) -> None:
        total = test_case.histogram.total
        assert_array_equal(total, test_case.expected_result)


class TestIterate:
    def test_iterate_yields_interval_value_pairs(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 3.0]), np.array([2.0, 6.0]))
        pairs = list(histogram.iterate())
        assert len(pairs) == 2
        assert pairs[0][0].left == 0.0
        assert pairs[0][0].right == 1.0
        assert pairs[0][1] == pytest.approx(2.0)
        assert pairs[1][0].left == 1.0
        assert pairs[1][0].right == 3.0
        assert pairs[1][1] == pytest.approx(6.0)


class TestFromConstant:
    def test_from_constant_uniform_bins(self) -> None:
        edges = np.array([0.0, 1.0, 2.0, 3.0])
        histogram = Histogram.from_constant(2.5, edges)
        np.testing.assert_array_almost_equal(histogram.values, [2.5, 2.5, 2.5])
        np.testing.assert_array_almost_equal(histogram.densities, [2.5, 2.5, 2.5])

    def test_from_constant_non_uniform_bins(self) -> None:
        edges = np.array([0.0, 1.0, 4.0])
        histogram = Histogram.from_constant(3.0, edges)
        assert histogram.values[0] == pytest.approx(3.0)
        assert histogram.values[1] == pytest.approx(9.0)
        np.testing.assert_array_almost_equal(histogram.densities, [3.0, 3.0])


class TestAstype:
    def test_astype_float32_to_float64(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float32), np.array([1.0, 2.0], dtype=np.float32))
        converted = histogram.astype(np.float64)
        assert converted.edges.dtype == np.float64
        assert converted.values.dtype == np.float64

    def test_astype_float64_to_float32(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float64), np.array([1.0, 2.0], dtype=np.float64))
        converted = histogram.astype(np.float32)
        assert converted.edges.dtype == np.float32
        assert converted.values.dtype == np.float32


class TestRebin:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        histogram: Histogram
        new_bins: Union[Array, Histogram, Interval]
        expected_result: Histogram
        description: str
        expect_warning: bool = False

        @property
        def test_id(self) -> str:
            return self.description

    test_cases = [
        TestCase(
            histogram=Histogram(
                np.array([2.0, 3.0, 5.0, 7.0], dtype=np.float64),
                np.array([4.0, 6.0, 8.0], dtype=np.float64),
            ),
            new_bins=np.array([2.0, 4.0, 7.0], dtype=np.float64),
            expected_result=Histogram(
                np.array([2.0, 4.0, 7.0], dtype=np.float64),
                np.array([7.0, 11.0], dtype=np.float64),
            ),
            description="coarser_binning_float64",
        ),
        TestCase(
            histogram=Histogram(
                np.array([1.0, 3.0, 6.0, 9.0], dtype=np.float32),
                np.array([6.0, 9.0, 12.0], dtype=np.float32),
            ),
            new_bins=np.array([1.0, 5.0, 9.0], dtype=np.float32),
            expected_result=Histogram(
                np.array([1.0, 5.0, 9.0], dtype=np.float32),
                np.array([12.0, 15.0], dtype=np.float32),
            ),
            description="coarser_binning_float32",
        ),
        TestCase(
            histogram=Histogram(
                np.array([5, 7, 10, 15], dtype=np.int64),
                np.array([4, 6, 10], dtype=np.int64),
            ),
            new_bins=np.array([5, 10, 15], dtype=np.int64),
            expected_result=Histogram(
                np.array([5.0, 10.0, 15.0], dtype=np.float64),
                np.array([10.0, 10.0], dtype=np.float64),
            ),
            description="coarser_binning_int64",
        ),
        TestCase(
            histogram=Histogram(
                np.array([3, 6, 10, 15], dtype=np.int32),
                np.array([9, 12, 15], dtype=np.int32),
            ),
            new_bins=np.array([3, 10, 15], dtype=np.int32),
            expected_result=Histogram(
                np.array([3.0, 10.0, 15.0], dtype=np.float64),
                np.array([21.0, 15.0], dtype=np.float64),
            ),
            description="coarser_binning_int32",
        ),
        TestCase(
            histogram=Histogram(
                np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64),
                np.array([2.0, 4.0, 6.0], dtype=np.float64),
            ),
            new_bins=np.array([1.0, 1.5, 2.5, 3.5, 4.0], dtype=np.float64),
            expected_result=Histogram(
                np.array([1.0, 1.5, 2.5, 3.5, 4.0], dtype=np.float64),
                np.array([1.0, 3.0, 5.0, 3.0], dtype=np.float64),
            ),
            description="finer_binning_float64",
        ),
        TestCase(
            histogram=Histogram(
                np.array([2.0, 4.0, 7.0], dtype=np.float32),
                np.array([8.0, 12.0], dtype=np.float32),
            ),
            new_bins=np.array([2.0, 3.0, 5.0, 7.0], dtype=np.float32),
            expected_result=Histogram(
                np.array([2.0, 3.0, 5.0, 7.0], dtype=np.float32),
                np.array([4.0, 8.0, 8.0], dtype=np.float32),
            ),
            description="finer_binning_float32",
        ),
        TestCase(
            histogram=Histogram(
                np.array([5, 7, 10], dtype=np.int64),
                np.array([6, 9], dtype=np.int64),
            ),
            new_bins=np.array([5.0, 6.5, 8.5, 10.0], dtype=np.float32),
            expected_result=Histogram(
                np.array([5.0, 6.5, 8.5, 10.0], dtype=np.float64),
                np.array([4.5, 6.0, 4.5], dtype=np.float64),
            ),
            description="finer_binning_mixed_dtype",
        ),
        TestCase(
            histogram=Histogram(
                np.array([2.0, 4.0, 7.0, 10.0], dtype=np.float64),
                np.array([6.0, 9.0, 12.0], dtype=np.float64),
            ),
            new_bins=Interval(2.0, 10.0),
            expected_result=Histogram(
                np.array([2.0, 10.0], dtype=np.float64),
                np.array([27.0], dtype=np.float64),
            ),
            description="single_bin_interval_exact_range_float64",
        ),
        TestCase(
            histogram=Histogram(
                np.array([3.0, 5.0, 8.0, 11.0], dtype=np.float32),
                np.array([4.0, 9.0, 6.0], dtype=np.float32),
            ),
            new_bins=Interval(np.float32(3.0), np.float32(11.0)),
            expected_result=Histogram(
                np.array([3.0, 11.0], dtype=np.float32),
                np.array([19.0], dtype=np.float32),
            ),
            description="single_bin_interval_exact_range_float32",
        ),
        TestCase(
            histogram=Histogram(
                np.array([2.0, 4.0, 7.0, 10.0], dtype=np.float64),
                np.array([6.0, 9.0, 12.0], dtype=np.float64),
            ),
            new_bins=Interval(np.float64(4.0), np.float64(7.0)),
            expected_result=Histogram(
                np.array([4.0, 7.0], dtype=np.float64),
                np.array([9.0], dtype=np.float64),
            ),
            description="single_bin_interval_inside_range_float64",
            expect_warning=True,
        ),
        TestCase(
            histogram=Histogram(
                np.array([5.0, 8.0, 12.0], dtype=np.float32),
                np.array([6.0, 14.0], dtype=np.float32),
            ),
            new_bins=Interval(np.float32(7.0), np.float32(11.0)),
            expected_result=Histogram(
                np.array([7.0, 11.0], dtype=np.float32),
                np.array([12.5], dtype=np.float32),
            ),
            description="single_bin_interval_inside_range_float32",
            expect_warning=True,
        ),
        TestCase(
            histogram=Histogram(
                np.array([5.0, 8.0, 12.0], dtype=np.float64),
                np.array([6.0, 14.0], dtype=np.float64),
            ),
            new_bins=Interval(8.0, 15.0),
            expected_result=Histogram(
                np.array([8.0, 15.0], dtype=np.float64),
                np.array([14.0], dtype=np.float64),
            ),
            description="single_bin_interval_overlapping_float64",
            expect_warning=True,
        ),
        TestCase(
            histogram=Histogram(
                np.array([4.0, 7.0, 10.0], dtype=np.float32),
                np.array([9.0, 12.0], dtype=np.float32),
            ),
            new_bins=Interval(np.float32(12.0), np.float32(20.0)),
            expected_result=Histogram(
                np.array([12.0, 20.0], dtype=np.float32),
                np.array([0.0], dtype=np.float32),
            ),
            description="single_bin_interval_disjoint_float32",
            expect_warning=True,
        ),
        TestCase(
            histogram=Histogram(
                np.array([2.0, 4.0, 7.0, 10.0], dtype=np.float64),
                np.array([6.0, 9.0, 12.0], dtype=np.float64),
            ),
            new_bins=np.array([2.0, 4.0, 7.0, 10.0], dtype=np.float64),
            expected_result=Histogram(
                np.array([2.0, 4.0, 7.0, 10.0], dtype=np.float64),
                np.array([6.0, 9.0, 12.0], dtype=np.float64),
            ),
            description="rebin_to_itself_float64",
        ),
        TestCase(
            histogram=Histogram(
                np.array([1.0, 3.0, 6.0, 9.0], dtype=np.float32),
                np.array([8.0, 12.0, 16.0], dtype=np.float32),
            ),
            new_bins=np.array([1.0, 3.0, 6.0, 9.0], dtype=np.float32),
            expected_result=Histogram(
                np.array([1.0, 3.0, 6.0, 9.0], dtype=np.float32),
                np.array([8.0, 12.0, 16.0], dtype=np.float32),
            ),
            description="rebin_to_itself_float32",
        ),
        TestCase(
            histogram=Histogram(
                np.array([5, 8, 12], dtype=np.int32),
                np.array([6, 14], dtype=np.int32),
            ),
            new_bins=Histogram(
                np.array([5, 8, 12], dtype=np.int32),
                np.array([1, 2], dtype=np.int32),
            ),
            expected_result=Histogram(
                np.array([5, 8, 12], dtype=np.float64),
                np.array([6, 14], dtype=np.float64),
            ),
            description="rebin_to_itself_int32",
        ),
        TestCase(
            histogram=Histogram(
                np.array([5.0, 8.0, 12.0], dtype=np.float64),
                np.array([6.0, 14.0], dtype=np.float64),
            ),
            new_bins=np.array([15.0, 18.0, 22.0], dtype=np.float64),
            expected_result=Histogram(
                np.array([15.0, 18.0, 22.0], dtype=np.float64),
                np.array([0.0, 0.0], dtype=np.float64),
            ),
            description="disjoint_bins_above_range",
            expect_warning=True,
        ),
        TestCase(
            histogram=Histogram(
                np.array([10.0, 15.0, 20.0], dtype=np.float32),
                np.array([8.0, 12.0], dtype=np.float32),
            ),
            new_bins=np.array([2.0, 5.0, 8.0], dtype=np.float32),
            expected_result=Histogram(
                np.array([2.0, 5.0, 8.0], dtype=np.float32),
                np.array([0.0, 0.0], dtype=np.float32),
            ),
            description="disjoint_bins_below_range",
            expect_warning=True,
        ),
        TestCase(
            histogram=Histogram(
                np.array([5.0, 8.0, 12.0], dtype=np.float64),
                np.array([6.0, 14.0], dtype=np.float64),
            ),
            new_bins=np.array([3.0, 7.0, 10.0, 15.0], dtype=np.float64),
            expected_result=Histogram(
                np.array([3.0, 7.0, 10.0, 15.0], dtype=np.float64),
                np.array([4.0, 9.0, 7.0], dtype=np.float64),
            ),
            description="extended_range_both_sides_float64",
        ),
        TestCase(
            histogram=Histogram(
                np.array([4.0, 7.0, 10.0], dtype=np.float32),
                np.array([9.0, 12.0], dtype=np.float32),
            ),
            new_bins=np.array([2.0, 5.0, 8.0, 12.0], dtype=np.float32),
            expected_result=Histogram(
                np.array([2.0, 5.0, 8.0, 12.0], dtype=np.float32),
                np.array([3.0, 10.0, 8.0], dtype=np.float32),
            ),
            description="extended_range_both_sides_float32",
        ),
        TestCase(
            histogram=Histogram(
                np.array([5, 10, 15], dtype=np.int64),
                np.array([10, 20], dtype=np.int64),
            ),
            new_bins=np.array([3.0, 8.0, 13.0, 18.0], dtype=np.float32),
            expected_result=Histogram(
                np.array([3.0, 8.0, 13.0, 18.0], dtype=np.float64),
                np.array([6.0, 16.0, 8.0], dtype=np.float64),
            ),
            description="extended_range_mixed_dtype",
        ),
        TestCase(
            histogram=Histogram(
                np.array([5.0, 8.0, 12.0, 16.0], dtype=np.float64),
                np.array([6.0, 9.0, 12.0], dtype=np.float64),
            ),
            new_bins=Histogram(
                np.array([25.0, 30.0, 36.0], dtype=np.float64),
                np.array([1.0, 2.0], dtype=np.float64),
            ),
            expected_result=Histogram(
                np.array([25.0, 30.0, 36.0], dtype=np.float64),
                np.array([0.0, 0.0], dtype=np.float64),
            ),
            description="rebin_with_disjoint_histogram_float64",
            expect_warning=True,
        ),
        TestCase(
            histogram=Histogram(
                np.array([2.0, 5.0, 9.0, 13.0], dtype=np.float32),
                np.array([8.0, 12.0, 16.0], dtype=np.float32),
            ),
            new_bins=Histogram(
                np.array([5.0, 7.0, 13.0], dtype=np.float32),
                np.array([3.0, 5.0], dtype=np.float32),
            ),
            expected_result=Histogram(
                np.array([5.0, 7.0, 13.0], dtype=np.float32),
                np.array([6.0, 22.0], dtype=np.float32),
            ),
            description="rebin_with_histogram_float32",
            expect_warning=True,
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_rebin(self, test_case: TestCase) -> None:
        if test_case.expect_warning:
            rebinned = expect_warning(
                test_case.histogram.rebin,
                RuntimeWarning,
                test_case.new_bins,
                match="outside",
            )
        else:
            rebinned = test_case.histogram.rebin(test_case.new_bins)

        assert_array_equal(rebinned.edges, test_case.expected_result.edges)
        assert_array_equal(rebinned.values, test_case.expected_result.values)

    def test_rebin_invalid_edges(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0]))
        with pytest.raises(ValueError, match="strictly increasing"):
            histogram.rebin(np.array([0.0, 2.0, 1.0]))


class TestValidateOverlap:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        histogram: Histogram
        new_edges: Array
        expect_warning: bool
        description: str

        @property
        def test_id(self) -> str:
            return self.description

    test_cases = [
        TestCase(
            histogram=Histogram(
                np.array([2.0, 5.0, 8.0], dtype=np.float64),
                np.array([6.0, 12.0], dtype=np.float64),
            ),
            new_edges=np.array([2.0, 5.0, 8.0], dtype=np.float64),
            expect_warning=False,
            description="edges_equal_no_warning",
        ),
        TestCase(
            histogram=Histogram(
                np.array([3.0, 5.0, 7.0], dtype=np.float32),
                np.array([4.0, 8.0], dtype=np.float32),
            ),
            new_edges=np.array([3.0, 5.0, 7.0], dtype=np.float32),
            expect_warning=False,
            description="edges_equal_float32_no_warning",
        ),
        TestCase(
            histogram=Histogram(
                np.array([3.0, 6.0, 10.0], dtype=np.float64),
                np.array([9.0, 12.0], dtype=np.float64),
            ),
            new_edges=np.array([1.0, 4.0, 7.0, 12.0], dtype=np.float64),
            expect_warning=False,
            description="edges_contained_in_new_edges_no_warning",
        ),
        TestCase(
            histogram=Histogram(
                np.array([5.0, 8.0, 12.0], dtype=np.float32),
                np.array([6.0, 14.0], dtype=np.float32),
            ),
            new_edges=np.array([3.0, 6.0, 9.0, 15.0], dtype=np.float32),
            expect_warning=False,
            description="edges_contained_float32_no_warning",
        ),
        TestCase(
            histogram=Histogram(
                np.array([2.0, 5.0, 10.0, 15.0], dtype=np.float64),
                np.array([8.0, 15.0, 20.0], dtype=np.float64),
            ),
            new_edges=np.array([2.0, 5.0, 10.0, 15.0], dtype=np.float64),
            expect_warning=False,
            description="exact_match_multiple_bins_no_warning",
        ),
        TestCase(
            histogram=Histogram(
                np.array([2.0, 5.0, 8.0], dtype=np.float64),
                np.array([6.0, 12.0], dtype=np.float64),
            ),
            new_edges=np.array([3.0, 6.0], dtype=np.float64),
            expect_warning=True,
            description="new_edges_contained_in_edges_warning",
        ),
        TestCase(
            histogram=Histogram(
                np.array([1.0, 5.0, 10.0], dtype=np.float32),
                np.array([8.0, 14.0], dtype=np.float32),
            ),
            new_edges=np.array([3.0, 7.0], dtype=np.float32),
            expect_warning=True,
            description="new_edges_inside_float32_warning",
        ),
        TestCase(
            histogram=Histogram(
                np.array([5.0, 8.0, 12.0], dtype=np.float64),
                np.array([6.0, 14.0], dtype=np.float64),
            ),
            new_edges=np.array([3.0, 7.0, 10.0], dtype=np.float64),
            expect_warning=True,
            description="overlapping_left_side_warning",
        ),
        TestCase(
            histogram=Histogram(
                np.array([5.0, 8.0, 12.0], dtype=np.float32),
                np.array([6.0, 14.0], dtype=np.float32),
            ),
            new_edges=np.array([7.0, 10.0, 15.0], dtype=np.float32),
            expect_warning=True,
            description="overlapping_right_side_warning",
        ),
        TestCase(
            histogram=Histogram(
                np.array([3.0, 6.0, 10.0], dtype=np.float64),
                np.array([9.0, 12.0], dtype=np.float64),
            ),
            new_edges=np.array([1.0, 4.0, 8.0, 12.0], dtype=np.float64),
            expect_warning=False,
            description="overlapping_both_sides_warning",
        ),
        TestCase(
            histogram=Histogram(
                np.array([5.0, 8.0, 12.0], dtype=np.float64),
                np.array([6.0, 14.0], dtype=np.float64),
            ),
            new_edges=np.array([15.0, 18.0, 22.0], dtype=np.float64),
            expect_warning=True,
            description="disjoint_above_warning",
        ),
        TestCase(
            histogram=Histogram(
                np.array([10.0, 15.0, 20.0], dtype=np.float32),
                np.array([8.0, 12.0], dtype=np.float32),
            ),
            new_edges=np.array([2.0, 5.0, 8.0], dtype=np.float32),
            expect_warning=True,
            description="disjoint_below_warning",
        ),
        TestCase(
            histogram=Histogram(
                np.array([5.0, 10.0, 15.0], dtype=np.float64),
                np.array([8.0, 12.0], dtype=np.float64),
            ),
            new_edges=np.array([20.0, 25.0, 30.0], dtype=np.float64),
            expect_warning=True,
            description="disjoint_far_above_warning",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_validate_overlap(self, test_case: TestCase) -> None:
        if test_case.expect_warning:
            expect_warning(test_case.histogram.validate_overlap, RuntimeWarning, test_case.new_edges, match="outside")
        else:
            test_case.histogram.validate_overlap(test_case.new_edges)


class TestRefine:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        histograms: Tuple[Histogram, ...]
        expected_result: Union[Array, Type[Exception]]
        match: Optional[str] = None
        test_id: str = ""

    test_cases = [
        TestCase(
            histograms=tuple(),
            expected_result=ValueError,
            match="At least one histogram is required",
            test_id="no_histograms_error",
        ),
        TestCase(
            histograms=(Histogram(np.array([1, 3, 7, 12], dtype=np.int32), np.array([5, 8, 3], dtype=np.int32)),),
            expected_result=np.array([1.0, 3.0, 7.0, 12.0], dtype=np.float64),
            test_id="single_histogram_int32_casted_to_float64",
        ),
        TestCase(
            histograms=(
                Histogram(
                    np.array([0.5, 2.3, 5.7, 9.1], dtype=np.float32),
                    np.array([1.2, 3.4, 5.6], dtype=np.float32),
                ),
            ),
            expected_result=np.array([0.5, 2.3, 5.7, 9.1], dtype=np.float32),
            test_id="single_histogram_float32_unchanged",
        ),
        TestCase(
            histograms=(
                Histogram(np.array([1.5, 4.2, 8.9, 15.3], dtype=np.float64), np.array([12.0, 34.0, 56.0])),
                Histogram(np.array([1.5, 4.2, 8.9, 15.3], dtype=np.float64), np.array([78.0, 90.0, 12.0])),
            ),
            expected_result=np.array([1.5, 4.2, 8.9, 15.3], dtype=np.float64),
            test_id="two_histograms_same_edges",
        ),
        TestCase(
            histograms=(
                Histogram(np.array([0.0, 5.0, 10.0], dtype=np.float32), np.array([3.0, 7.0], dtype=np.float32)),
                Histogram(
                    np.array([0.0, 2.5, 5.0, 7.5, 10.0], dtype=np.float32),
                    np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32),
                ),
            ),
            expected_result=np.array([0.0, 2.5, 5.0, 7.5, 10.0], dtype=np.float32),
            test_id="two_histograms_one_refined",
        ),
        TestCase(
            histograms=(
                Histogram(
                    np.array([1.0, 3.0, 5.0, 8.0, 12.0], dtype=np.float64),
                    np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float64),
                ),
                Histogram(np.array([3.0, 5.0, 8.0], dtype=np.float64), np.array([15.0, 25.0], dtype=np.float64)),
            ),
            expected_result=np.array([1.0, 3.0, 5.0, 8.0, 12.0], dtype=np.float64),
            test_id="two_histograms_subset_with_endpoints",
        ),
        TestCase(
            histograms=(
                Histogram(
                    np.array([0.0, 2.0, 5.0, 9.0, 15.0], dtype=np.float32), np.array([5, 10, 15, 20], dtype=np.int8)
                ),
                Histogram(np.array([2.0, 5.0, 9.0], dtype=np.float32), np.array([8, 12], dtype=np.int8)),
            ),
            expected_result=np.array([0.0, 2.0, 5.0, 9.0, 15.0], dtype=np.float32),
            test_id="two_histograms_subset_without_endpoints",
        ),
        TestCase(
            histograms=(
                Histogram(np.array([0.0, 3.0, 6.0], dtype=np.float64), np.array([12.0, 24.0])),
                Histogram(np.array([0.0, 2.0, 4.0, 6.0], dtype=np.float64), np.array([8.0, 16.0, 32.0])),
            ),
            expected_result=np.array([0.0, 2.0, 3.0, 4.0, 6.0], dtype=np.float64),
            test_id="two_histograms_same_support_different_bins",
        ),
        TestCase(
            histograms=(
                Histogram(np.array([1.0, 4.0, 7.0, 11.0], dtype=np.float32), np.array([5.0, 10.0, 15.0])),
                Histogram(np.array([4.0, 8.0, 11.0, 15.0], dtype=np.float32), np.array([20.0, 25.0, 30.0])),
            ),
            expected_result=np.array([1.0, 4.0, 7.0, 8.0, 11.0, 15.0], dtype=np.float64),  # because values are float64
            test_id="overlapping_histograms_with_edge_points_overlapping",
        ),
        TestCase(
            histograms=(
                Histogram(np.array([0.0, 3.5, 7.2], dtype=np.float64), np.array([12.0, 18.0])),
                Histogram(np.array([2.1, 5.8, 6.9], dtype=np.float64), np.array([9.0, 15.0])),
            ),
            expected_result=np.array([0.0, 2.1, 3.5, 5.8, 6.9, 7.2], dtype=np.float64),
            test_id="overlapping_histograms_without_edge_points_overlapping",
        ),
        TestCase(
            histograms=(
                Histogram(np.array([1.0, 3.0, 5.0], dtype=np.float32), np.array([8.0, 12.0], dtype=np.float32)),
                Histogram(np.array([10.0, 15.0, 20.0], dtype=np.float32), np.array([16.0, 24.0], dtype=np.float32)),
            ),
            expected_result=np.array([1.0, 3.0, 5.0, 10.0, 15.0, 20.0], dtype=np.float32),
            test_id="disjoint_histograms",
        ),
        TestCase(
            histograms=(
                Histogram(np.array([0.0, 2.5, 5.0], dtype=np.float64), np.array([10.0, 20.0])),
                Histogram(np.array([1.0, 3.0, 5.0], dtype=np.float64), np.array([15.0, 25.0])),
                Histogram(np.array([0.0, 1.5, 4.0, 5.0], dtype=np.float64), np.array([5.0, 12.0, 18.0])),
            ),
            expected_result=np.array([0.0, 1.0, 1.5, 2.5, 3.0, 4.0, 5.0], dtype=np.float64),
            test_id="three_histograms",
        ),
        TestCase(
            histograms=(
                Histogram(np.array([10.0, 20.0, 35.0, 50.0]), np.array([8.0, 16.0, 24.0])),
                Histogram(np.array([10.0, 15.0, 25.0, 35.0, 50.0]), np.array([4.0, 8.0, 12.0, 16.0])),
                Histogram(np.array([10.0, 30.0, 40.0, 50.0]), np.array([20.0, 30.0, 40.0])),
                Histogram(np.array([15.0, 25.0, 35.0, 45.0, 50.0]), np.array([5.0, 10.0, 15.0, 20.0])),
            ),
            expected_result=np.array([10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0], dtype=np.float32),
            test_id="four_histograms",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.test_id,
    )
    def test_refine(self, test_case: TestCase) -> None:
        if isinstance(test_case.expected_result, type) and issubclass(test_case.expected_result, Exception):
            expect_error(
                Histogram.refine,
                test_case.expected_result,
                *test_case.histograms,
                match=test_case.match,
            )
        else:
            refined = Histogram.refine(*test_case.histograms)
            assert len(refined) == len(test_case.histograms)
            for histogram in refined:
                assert_array_equal(histogram.edges, test_case.expected_result)
                assert histogram.edges.dtype == test_case.expected_result.dtype


class TestApply:
    def test_apply_square_function(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 4.0]), np.array([2.0, 6.0]))
        result = Histogram.apply(lambda d: d**2, histogram)
        np.testing.assert_array_almost_equal(result.densities, [4.0, 4.0])

    def test_apply_add_constant(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0]))
        result = Histogram.apply(lambda d: d + 5.0, histogram)
        np.testing.assert_array_almost_equal(result.densities, [6.0, 7.0])

    def test_apply_multiply_constant(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 4.0]), np.array([2.0, 6.0]))
        result = Histogram.apply(lambda d: d * 3.0, histogram)
        np.testing.assert_array_almost_equal(result.densities, [6.0, 6.0])

    def test_apply_log_function(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 4.0]), np.array([np.e, 3 * np.e]))
        result = Histogram.apply(np.log, histogram)
        np.testing.assert_array_almost_equal(result.densities, [1.0, 1.0])

    def test_apply_exp_function(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 4.0]), np.array([1.0, 3.0]))
        result = Histogram.apply(np.exp, histogram)
        np.testing.assert_array_almost_equal(result.densities, [np.e, np.e])

    def test_apply_multiple_histograms(self) -> None:
        histogram1 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0]))
        histogram2 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0]))
        result = Histogram.apply(lambda d1, d2: d1 + d2, histogram1, histogram2)
        np.testing.assert_array_almost_equal(result.densities, [3.0, 6.0])

    def test_apply_with_mismatched_edges(self) -> None:
        histogram1 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0]))
        histogram2 = Histogram(np.array([0.0, 1.0, 3.0]), np.array([2.0, 4.0]))
        with pytest.raises(ValueError, match="same edges"):
            Histogram.apply(lambda d1, d2: d1 + d2, histogram1, histogram2)


class TestApplyWith:
    def test_apply_with_convenience_method(self) -> None:
        histogram1 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0]))
        histogram2 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0]))
        result = histogram1.apply_with(lambda d1, d2: d1 * d2, histogram2)
        np.testing.assert_array_almost_equal(result.densities, [2.0, 8.0])


class TestReduce:
    def test_reduce_add_two_histograms(self) -> None:
        histogram1 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0]))
        histogram2 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0]))
        result = Histogram.reduce(np.add, histogram1, histogram2)
        np.testing.assert_array_almost_equal(result.densities, [3.0, 6.0])

    def test_reduce_multiply_two_histograms(self) -> None:
        histogram1 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0]))
        histogram2 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([3.0, 6.0]))
        result = Histogram.reduce(np.multiply, histogram1, histogram2)
        np.testing.assert_array_almost_equal(result.densities, [6.0, 24.0])

    def test_reduce_three_histograms(self) -> None:
        histogram1 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0]))
        histogram2 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0]))
        histogram3 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([3.0, 6.0]))
        result = Histogram.reduce(np.add, histogram1, histogram2, histogram3)
        np.testing.assert_array_almost_equal(result.densities, [6.0, 12.0])

    def test_reduce_single_histogram(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0]))
        result = Histogram.reduce(np.add, histogram)
        assert result == histogram

    def test_reduce_with_mismatched_edges(self) -> None:
        histogram1 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0]))
        histogram2 = Histogram(np.array([0.0, 1.0, 3.0]), np.array([2.0, 4.0]))
        with pytest.raises(ValueError, match="same edges"):
            Histogram.reduce(np.add, histogram1, histogram2)


class TestReduceWith:
    def test_reduce_with_convenience_method(self) -> None:
        histogram1 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0]))
        histogram2 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([3.0, 6.0]))
        result = histogram1.reduce_with(np.multiply, histogram2)
        np.testing.assert_array_almost_equal(result.densities, [6.0, 24.0])


class TestAddition:
    def test_add_two_histograms_same_edges(self) -> None:
        histogram1 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0]))
        histogram2 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0]))
        result = histogram1 + histogram2
        np.testing.assert_array_almost_equal(result.values, [3.0, 6.0])

    def test_add_two_histograms_different_edges(self) -> None:
        histogram1 = Histogram(np.array([0.0, 1.0, 3.0]), np.array([2.0, 6.0]))
        histogram2 = Histogram(np.array([0.0, 2.0, 3.0]), np.array([4.0, 3.0]))
        result = histogram1 + histogram2
        expected_edges = np.array([0.0, 1.0, 2.0, 3.0])
        np.testing.assert_array_almost_equal(result.edges, expected_edges)
        assert result.total == pytest.approx(histogram1.total + histogram2.total)

    def test_add_scalar_to_histogram(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 4.0]), np.array([2.0, 6.0]))
        result = histogram + 3.0
        np.testing.assert_array_almost_equal(result.densities, [5.0, 5.0])

    def test_radd_scalar_to_histogram(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 4.0]), np.array([2.0, 6.0]))
        result = 3.0 + histogram
        np.testing.assert_array_almost_equal(result.densities, [5.0, 5.0])

    def test_add_array_to_histogram(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0]))
        array = np.array([2.0, 3.0])
        result = histogram + array
        np.testing.assert_array_almost_equal(result.values, [3.0, 5.0])

    def test_radd_array_to_histogram(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0]))
        array = np.array([2.0, 3.0])
        result = array + histogram
        np.testing.assert_array_almost_equal(result.values, [3.0, 5.0])

    def test_add_array_wrong_length(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0]))
        array = np.array([2.0, 3.0, 4.0])
        with pytest.raises(ValueError, match="must match"):
            _ = histogram + array


class TestSubtraction:
    def test_subtract_two_histograms_same_edges(self) -> None:
        histogram1 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([3.0, 6.0]))
        histogram2 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0]))
        result = histogram1 - histogram2
        np.testing.assert_array_almost_equal(result.values, [2.0, 4.0])

    def test_subtract_two_histograms_different_edges(self) -> None:
        histogram1 = Histogram(np.array([0.0, 1.0, 3.0]), np.array([3.0, 9.0]))
        histogram2 = Histogram(np.array([0.0, 2.0, 3.0]), np.array([2.0, 3.0]))
        result = histogram1 - histogram2
        expected_edges = np.array([0.0, 1.0, 2.0, 3.0])
        np.testing.assert_array_almost_equal(result.edges, expected_edges)

    def test_subtract_scalar_from_histogram(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 4.0]), np.array([5.0, 15.0]))
        result = histogram - 2.0
        np.testing.assert_array_almost_equal(result.densities, [3.0, 3.0])

    def test_rsub_scalar_from_histogram(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 4.0]), np.array([2.0, 6.0]))
        result = 5.0 - histogram
        np.testing.assert_array_almost_equal(result.densities, [3.0, 3.0])

    def test_subtract_array_from_histogram(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0]), np.array([5.0, 7.0]))
        array = np.array([2.0, 3.0])
        result = histogram - array
        np.testing.assert_array_almost_equal(result.values, [3.0, 4.0])

    def test_rsub_array_from_histogram(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0]))
        array = np.array([5.0, 7.0])
        result = array - histogram
        np.testing.assert_array_almost_equal(result.values, [4.0, 5.0])


class TestMultiplication:
    def test_multiply_two_histograms_same_edges(self) -> None:
        histogram1 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0]))
        histogram2 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([3.0, 6.0]))
        result = histogram1 * histogram2
        np.testing.assert_array_almost_equal(result.densities, [6.0, 24.0])

    def test_multiply_two_histograms_different_edges(self) -> None:
        histogram1 = Histogram(np.array([0.0, 1.0, 3.0]), np.array([2.0, 6.0]))
        histogram2 = Histogram(np.array([0.0, 2.0, 3.0]), np.array([4.0, 3.0]))
        result = histogram1 * histogram2
        expected_edges = np.array([0.0, 1.0, 2.0, 3.0])
        np.testing.assert_array_almost_equal(result.edges, expected_edges)

    def test_multiply_scalar_with_histogram(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 4.0]), np.array([2.0, 6.0]))
        result = histogram * 3.0
        np.testing.assert_array_almost_equal(result.values, [6.0, 18.0])

    def test_rmul_scalar_with_histogram(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 4.0]), np.array([2.0, 6.0]))
        result = 3.0 * histogram
        np.testing.assert_array_almost_equal(result.values, [6.0, 18.0])

    def test_multiply_array_with_histogram(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0]))
        array = np.array([3.0, 2.0])
        result = histogram * array
        expected_densities = [2.0 * 3.0, 2.0 * 2.0]
        np.testing.assert_array_almost_equal(result.densities, expected_densities)

    def test_rmul_array_with_histogram(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0]))
        array = np.array([3.0, 2.0])
        result = array * histogram
        expected_densities = [2.0 * 3.0, 2.0 * 2.0]
        np.testing.assert_array_almost_equal(result.densities, expected_densities)

    def test_multiply_array_wrong_length(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0]))
        array = np.array([2.0, 3.0, 4.0])
        with pytest.raises(ValueError, match="must match"):
            _ = histogram * array


class TestDivision:
    def test_divide_histogram_by_scalar(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 4.0]), np.array([6.0, 18.0]))
        result = histogram / 3.0
        np.testing.assert_array_almost_equal(result.values, [2.0, 6.0])

    def test_divide_histogram_by_histogram(self) -> None:
        histogram1 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([6.0, 12.0]))
        histogram2 = Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0]))
        result = histogram1 / histogram2
        np.testing.assert_array_almost_equal(result.densities, [3.0, 3.0])

    def test_divide_histogram_by_array(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0]), np.array([6.0, 12.0]))
        array = np.array([2.0, 3.0])
        result = histogram / array
        np.testing.assert_array_almost_equal(result.values, [3.0, 4.0])

    def test_rtruediv_scalar_by_histogram(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 4.0]), np.array([2.0, 6.0]))
        result = 6.0 / histogram
        np.testing.assert_array_almost_equal(result.densities, [3.0, 3.0])

    def test_rtruediv_array_by_histogram(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0]))
        array = np.array([6.0, 12.0])
        result = array / histogram
        np.testing.assert_array_almost_equal(result.values, [3.0, 3.0])

    def test_divide_array_wrong_length(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0]))
        array = np.array([2.0, 3.0, 4.0])
        with pytest.raises(ValueError, match="must match"):
            _ = histogram / array


class TestPower:
    def test_power_square(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 4.0]), np.array([2.0, 6.0]))
        result = histogram**2
        np.testing.assert_array_almost_equal(result.densities, [4.0, 4.0])

    def test_power_cube(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0]))
        result = histogram**3
        np.testing.assert_array_almost_equal(result.densities, [8.0, 8.0])

    def test_power_inverse(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 4.0]), np.array([2.0, 6.0]))
        result = histogram**-1
        np.testing.assert_array_almost_equal(result.densities, [0.5, 0.5])

    def test_power_fractional(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 4.0]), np.array([4.0, 12.0]))
        result = histogram**0.5
        np.testing.assert_array_almost_equal(result.densities, [2.0, 2.0])


class TestEdgeCases:
    def test_empty_histogram_operations(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0]), np.array([5.0]))
        assert len(histogram) == 1
        assert histogram.total == pytest.approx(5.0)

    def test_histogram_with_zero_values(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0]), np.array([0.0, 0.0]))
        assert histogram.total == pytest.approx(0.0)
        np.testing.assert_array_almost_equal(histogram.densities, [0.0, 0.0])

    def test_histogram_with_negative_values(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0]), np.array([-1.0, 2.0]))
        assert histogram.total == pytest.approx(1.0)
        assert histogram.density(0) == pytest.approx(-1.0)

    def test_histogram_arithmetic_preserves_type(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0], dtype=np.float32), np.array([1.0, 2.0], dtype=np.float32))
        result = histogram + histogram
        assert result.edges.dtype == np.float32

    def test_complex_operation_chain(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 4.0]), np.array([2.0, 6.0]))
        result = ((histogram + 1.0) * 2.0) ** 2 - 1.0
        assert isinstance(result, Histogram)
        assert len(result) == len(histogram)

    def test_refine_with_many_histograms(self) -> None:
        histograms = [
            Histogram(np.array([0.0, 1.0, 4.0]), np.array([2.0, 6.0])),
            Histogram(np.array([0.0, 2.0, 4.0]), np.array([4.0, 6.0])),
            Histogram(np.array([0.0, 0.5, 4.0]), np.array([1.0, 9.5])),
        ]
        refined = Histogram.refine(*histograms)
        expected_edges = np.array([0.0, 0.5, 1.0, 2.0, 4.0])
        for hist in refined:
            np.testing.assert_array_almost_equal(hist.edges, expected_edges)
        for original, refined_hist in zip(histograms, refined):
            assert refined_hist.total == pytest.approx(original.total)
