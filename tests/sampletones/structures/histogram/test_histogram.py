from dataclasses import dataclass
from types import ModuleType
from typing import Any, Optional, Tuple, Type, Union

import numpy as np
import pytest
from pydantic import ValidationError

from sampletones import xp
from sampletones.structures.histogram.histogram import Histogram
from sampletones.structures.histogram.interval import Interval
from sampletones.types.array import Array, Float, Numeric
from tests.sampletones.arrays import assert_array_equal
from tests.sampletones.errors import expect_error, expect_warning


class TestInit:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        edges: Any
        values: Any
        expected_result: Union[Histogram, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            edges=np.array([0.0, 1.0, 2.0], dtype=np.float64),
            values=np.array([1.0, 2.0], dtype=np.float64),
            expected_result=Histogram(
                np.array([0.0, 1.0, 2.0], dtype=np.float64), np.array([1.0, 2.0], dtype=np.float64)
            ),
            test_id="basic_float64_array",
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 4.0], dtype=np.float32),
            values=np.array([2.0, 6.0], dtype=np.float32),
            expected_result=Histogram(
                np.array([0.0, 1.0, 4.0], dtype=np.float32), np.array([2.0, 6.0], dtype=np.float32)
            ),
            test_id="basic_float32_array",
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 2.0, 3.0], dtype=np.float32),
            values=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            expected_result=Histogram(
                np.array([0.0, 1.0, 2.0, 3.0], dtype=np.float32), np.array([1.0, 2.0, 3.0], dtype=np.float32)
            ),
            test_id="three_bins_float32",
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 4.0], dtype=np.float32),
            values=np.float32(3.0),
            expected_result=Histogram(
                np.array([0.0, 1.0, 4.0], dtype=np.float32), np.array([3.0, 9.0], dtype=np.float32)
            ),
            test_id="constant_density_float32",
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 4.0], dtype=np.float64),
            values=np.float64(3.0),
            expected_result=Histogram(
                np.array([0.0, 1.0, 4.0], dtype=np.float64), np.array([3.0, 9.0], dtype=np.float64)
            ),
            test_id="constant_density_float64",
        ),
        TestCase(
            edges=np.array([0, 1, 2], dtype=np.int64),
            values=np.array([1, 2], dtype=np.int64),
            expected_result=Histogram(np.array([0, 1, 2], dtype=np.int64), np.array([1, 2], dtype=np.int64)),
            test_id="integer_int64",
        ),
        TestCase(
            edges=np.array([0, 1, 4], dtype=np.int32),
            values=np.array([2, 6], dtype=np.int32),
            expected_result=Histogram(np.array([0, 1, 4], dtype=np.int32), np.array([2, 6], dtype=np.int32)),
            test_id="integer_int32",
        ),
        TestCase(
            edges=np.array([0.0, 1.0, np.inf], dtype=np.float32),
            values=np.array([1.0, 2.0], dtype=np.float32),
            expected_result=ValidationError,
            test_id="edges_with_positive_inf",
        ),
        TestCase(
            edges=np.array([-np.inf, 0.0, np.inf], dtype=np.float64),
            values=np.array([1.0, 2.0], dtype=np.float64),
            expected_result=ValidationError,
            test_id="edges_with_negative_and_positive_inf",
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 2.0], dtype=np.float32),
            values=np.array([np.nan, 2.0], dtype=np.float32),
            expected_result=ValidationError,
            test_id="values_with_nan",
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 2.0], dtype=np.float64),
            values=np.array([1.0], dtype=np.float64),
            expected_result=ValueError,
            match="edges should have exactly",
            test_id="too_many_edges",
        ),
        TestCase(
            edges=np.array([0.0, 1.0], dtype=np.float32),
            values=np.array([1.0, 2.0], dtype=np.float32),
            expected_result=ValueError,
            match="edges should have exactly",
            test_id="too_few_edges",
        ),
        TestCase(
            edges=np.array([0.0], dtype=np.float64),
            values=np.array([], dtype=np.float64),
            expected_result=ValueError,
            match="At least two edges",
            test_id="single_edge",
        ),
        TestCase(
            edges=np.array([2.0, 1.0, 3.0], dtype=np.float32),
            values=np.array([1.0, 2.0], dtype=np.float32),
            expected_result=ValueError,
            match="strictly increasing",
            test_id="edges_not_monotonic",
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 1.0, 2.0], dtype=np.float64),
            values=np.array([1.0, 2.0, 3.0], dtype=np.float64),
            expected_result=ValueError,
            match="strictly increasing",
            test_id="edges_with_duplicate",
        ),
        TestCase(
            edges=np.array([0, 1, 0], dtype=np.int32),
            values=np.array([1, 2], dtype=np.int32),
            expected_result=ValueError,
            match="strictly increasing",
            test_id="edges_decreasing",
        ),
        TestCase(
            edges=np.array([[0.0, 1.0], [2.0, 3.0]], dtype=np.float32),
            values=np.array([1.0], dtype=np.float32),
            expected_result=ValueError,
            match="edges must be a one-dimensional array",
            test_id="edges_2d_array",
        ),
        TestCase(
            edges=[0.0, 1.0, 2.0],
            values=np.array([1.0, 2.0], dtype=np.float32),
            expected_result=ValidationError,
            test_id="edges_as_list",
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 2.0], dtype=np.float32),
            values=[1.0, 2.0],
            expected_result=ValidationError,
            test_id="values_as_list",
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 2.0], dtype=np.float32),
            values=xp.array([1.0, 2.0], dtype=xp.float32),
            expected_result=TypeError,
            match="edges and values must be of the same type",
            test_id="edges_numpy_values_cupy_type_mismatch",
        ),
        TestCase(
            edges=Interval(0.0, 5.0),
            values=np.array([10.0], dtype=np.float32),
            expected_result=Histogram(np.array([0.0, 5.0]), np.array([10.0], dtype=np.float32)),
            test_id="interval_with_array_values",
        ),
        TestCase(
            edges=Interval(np.float32(0.0), np.float32(5.0)),
            values=np.float32(3.0),
            expected_result=Histogram(np.array([0.0, 5.0], dtype=np.float32), np.array([15.0], dtype=np.float32)),
            test_id="interval_with_constant_density_float32",
        ),
        TestCase(
            edges=Interval(2.0, 8.0),
            values=np.array([12.0], dtype=np.float64),
            expected_result=Histogram(np.array([2.0, 8.0], dtype=np.float64), np.array([12.0], dtype=np.float64)),
            test_id="interval_with_array_values_float64",
        ),
        TestCase(
            edges=Interval(-5.0, 5.0),
            values=np.float64(2.0),
            expected_result=Histogram(np.array([-5.0, 5.0], dtype=np.float64), np.array([20.0], dtype=np.float64)),
            test_id="interval_with_constant_density_float64",
        ),
        TestCase(
            edges=Interval(1.0, -1.0),
            values=np.array([10.0], dtype=np.float32),
            expected_result=ValidationError,
            match="strictly increasing",
            test_id="interval_invalid_left_greater_than_right",
        ),
        TestCase(
            edges=Interval(0.0, 0.0),
            values=np.array([10.0], dtype=np.float32),
            expected_result=ValidationError,
            match="strictly increasing",
            test_id="interval_empty_equal_bounds",
        ),
        TestCase(
            edges=Interval(np.nan, 5.0),
            values=np.array([10.0], dtype=np.float32),
            expected_result=ValidationError,
            match="edges must contain only finite values",
            test_id="interval_with_nan_left",
        ),
        TestCase(
            edges=Interval(0.0, np.nan),
            values=np.array([10.0], dtype=np.float32),
            expected_result=ValidationError,
            match="edges must contain only finite values",
            test_id="interval_with_nan_right",
        ),
        TestCase(
            edges=Interval(-np.inf, 5.0),
            values=np.array([10.0], dtype=np.float32),
            expected_result=ValidationError,
            match="edges must contain only finite values",
            test_id="interval_with_negative_inf_left",
        ),
        TestCase(
            edges=Interval(0.0, np.inf),
            values=np.array([10.0], dtype=np.float32),
            expected_result=ValidationError,
            match="edges must contain only finite values",
            test_id="interval_with_positive_inf_right",
        ),
        TestCase(
            edges=Interval(-np.inf, np.inf),
            values=np.float32(1.0),
            expected_result=ValidationError,
            match="edges must contain only finite values",
            test_id="interval_unbounded_both_sides",
        ),
        TestCase(
            edges=xp.array([0.0, 1.0, 2.0]),
            values=np.array([1.0, 2.0]),
            expected_result=TypeError,
            match="edges and values must be of the same type",
            test_id="mismatched_types_cupy_edges_numpy_values",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.test_id)
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


class TestValidateHistogramEdges:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        histograms: Tuple[Histogram, ...]
        equal_edges: bool
        expected_result: Union[None, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            histograms=(
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([3.0, 4.0])),
            ),
            equal_edges=True,
            expected_result=None,
            test_id="same_edges_two_histograms_numpy",
        ),
        TestCase(
            histograms=(
                Histogram(np.array([0.0, 1.0, 2.0, 3.0]), np.array([1.0, 2.0, 3.0])),
                Histogram(np.array([0.0, 1.0, 2.0, 3.0]), np.array([4.0, 5.0, 6.0])),
                Histogram(np.array([0.0, 1.0, 2.0, 3.0]), np.array([7.0, 8.0, 9.0])),
            ),
            equal_edges=True,
            expected_result=None,
            test_id="same_edges_three_histograms_numpy",
        ),
        TestCase(
            histograms=(
                Histogram(xp.array([0.0, 1.0, 2.0]), xp.array([1.0, 2.0])),
                Histogram(xp.array([0.0, 1.0, 2.0]), xp.array([3.0, 4.0])),
            ),
            equal_edges=True,
            expected_result=None,
            test_id="same_edges_two_histograms_cupy",
        ),
        TestCase(
            histograms=(
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
                Histogram(np.array([0.0, 1.5, 2.0]), np.array([3.0, 4.0])),
            ),
            equal_edges=True,
            expected_result=ValueError,
            match="All histograms must have the same edges",
            test_id="different_edges_equal_edges_true_raises",
        ),
        TestCase(
            histograms=(
                Histogram(np.array([0.0, 1.0, 2.0, 3.0]), np.array([1.0, 2.0, 3.0])),
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([4.0, 5.0])),
            ),
            equal_edges=True,
            expected_result=ValueError,
            match="All histograms must have the same edges",
            test_id="different_lengths_equal_edges_true_raises",
        ),
        TestCase(
            histograms=(
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
                Histogram(np.array([0.0, 1.5, 2.5]), np.array([3.0, 4.0])),
            ),
            equal_edges=False,
            expected_result=None,
            test_id="different_edges_equal_edges_false_allowed",
        ),
        TestCase(
            histograms=(
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
                Histogram(np.array([1.0, 2.0, 3.0, 4.0]), np.array([3.0, 4.0, 5.0])),
                Histogram(np.array([0.5, 1.5, 2.5]), np.array([6.0, 7.0])),
            ),
            equal_edges=False,
            expected_result=None,
            test_id="different_edges_multiple_histograms_equal_edges_false_allowed",
        ),
        TestCase(
            histograms=(),
            equal_edges=True,
            expected_result=ValueError,
            match="At least one histogram is required",
            test_id="no_histograms_raises",
        ),
        TestCase(
            histograms=(
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
                Histogram(xp.array([0.0, 1.0, 2.0]), xp.array([3.0, 4.0])),
            ),
            equal_edges=True,
            expected_result=TypeError,
            match="All histograms must be of the same array type",
            test_id="mixed_numpy_cupy_raises",
        ),
        TestCase(
            histograms=(
                Histogram(xp.array([0.0, 1.0, 2.0]), xp.array([1.0, 2.0])),
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([3.0, 4.0])),
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([5.0, 6.0])),
            ),
            equal_edges=False,
            expected_result=TypeError,
            match="All histograms must be of the same array type",
            test_id="mixed_numpy_cupy_multiple_histograms_raises",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.test_id)
    def test_validate_histogram_edges(self, test_case: TestCase) -> None:
        expect_error(
            Histogram._validate_histogram_edges,
            test_case.expected_result,
            *test_case.histograms,
            equal_edges=test_case.equal_edges,
            match=test_case.match,
        )


class TestValidateArrayLengths:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        histogram: Histogram
        arrays: Tuple[Array, ...]
        expected_result: Union[None, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
            arrays=(np.array([3.0, 4.0]), np.array([5.0, 6.0])),
            expected_result=None,
            test_id="matching_lengths_two_arrays",
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 2.0, 3.0]), np.array([1.0, 2.0, 3.0])),
            arrays=(np.array([4.0, 5.0, 6.0]), np.array([7.0, 8.0, 9.0]), np.array([10.0, 11.0, 12.0])),
            expected_result=None,
            test_id="matching_lengths_three_arrays",
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
            arrays=(np.array([3.0, 4.0, 5.0]),),
            expected_result=ValueError,
            match="Array length 3 must match values length 2",
            test_id="mismatched_length_single_array_raises",
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 2.0, 3.0]), np.array([1.0, 2.0, 3.0])),
            arrays=(np.array([4.0, 5.0, 6.0]), np.array([7.0, 8.0])),
            expected_result=ValueError,
            match="Array length 2 must match values length 3",
            test_id="mismatched_length_second_array_raises",
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 2.0, 3.0, 4.0]), np.array([1.0, 2.0, 3.0, 4.0])),
            arrays=(np.array([5.0]), np.array([6.0, 7.0, 8.0, 9.0])),
            expected_result=ValueError,
            match="Array length 1 must match values length 4",
            test_id="mismatched_length_first_array_raises",
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
            arrays=(),
            expected_result=None,
            test_id="no_arrays_passes",
        ),
        TestCase(
            histogram=Histogram(xp.array([0.0, 1.0, 2.0]), xp.array([1.0, 2.0])),
            arrays=(xp.array([3.0, 4.0]),),
            expected_result=None,
            test_id="matching_lengths_cupy_arrays",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.test_id)
    def test_validate_array_lengths(self, test_case: TestCase) -> None:
        expect_error(
            test_case.histogram._validate_array_lengths,
            test_case.expected_result,
            *test_case.arrays,
            match=test_case.match,
        )


class TestValidateNegativePower:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        base: Union[Numeric, Array, Histogram]
        exponent: Union[Numeric, Array, Histogram]
        expected_result: Union[None, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            base=2.0,
            exponent=-1.0,
            expected_result=None,
            test_id="scalar_base_scalar_exponent_valid",
        ),
        TestCase(
            base=0.0,
            exponent=2.0,
            expected_result=None,
            test_id="scalar_base_zero_positive_exponent",
        ),
        TestCase(
            base=0.0,
            exponent=0.0,
            expected_result=None,
            test_id="scalar_base_zero_zero_exponent",
        ),
        TestCase(
            base=0.0,
            exponent=-1.0,
            expected_result=ZeroDivisionError,
            match="Zero cannot be raised to a negative power",
            test_id="scalar_base_zero_negative_exponent_raises",
        ),
        TestCase(
            base=np.array([1.0, 2.0, 3.0]),
            exponent=-2.0,
            expected_result=None,
            test_id="array_base_scalar_exponent_valid",
        ),
        TestCase(
            base=np.array([0.0, 2.0, 3.0]),
            exponent=2.0,
            expected_result=None,
            test_id="array_base_scalar_exponent_with_zeros_positive_exponent",
        ),
        TestCase(
            base=np.array([0.0, 2.0, 3.0]),
            exponent=-1.0,
            expected_result=ZeroDivisionError,
            match="Zero densities cannot be raised to negative powers",
            test_id="array_base_scalar_exponent_with_zeros_negative_exponent_raises",
        ),
        TestCase(
            base=np.array([1.0, 2.0, 3.0]),
            exponent=np.array([-1.0, -2.0, -3.0]),
            expected_result=None,
            test_id="array_base_array_exponent_valid",
        ),
        TestCase(
            base=np.array([0.0, 2.0, 3.0]),
            exponent=np.array([1.0, -1.0, -2.0]),
            expected_result=None,
            test_id="array_base_array_exponent_mixed_valid",
        ),
        TestCase(
            base=np.array([1.0, 0.0, 3.0]),
            exponent=np.array([1.0, -1.0, 2.0]),
            expected_result=ZeroDivisionError,
            match="Zero densities cannot be raised to negative powers",
            test_id="array_base_array_exponent_zero_base_negative_exponent_raises",
        ),
        TestCase(
            base=2.0,
            exponent=np.array([-1.0, -2.0, -3.0]),
            expected_result=None,
            test_id="scalar_base_array_exponent_valid",
        ),
        TestCase(
            base=0.0,
            exponent=np.array([1.0, -1.0, 2.0]),
            expected_result=ZeroDivisionError,
            match="Zero densities cannot be raised to negative powers",
            test_id="scalar_base_zero_array_exponent_with_negative_raises",
        ),
        TestCase(
            base=Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0])),
            exponent=-1.0,
            expected_result=None,
            test_id="histogram_base_scalar_exponent_valid",
        ),
        TestCase(
            base=Histogram(np.array([0.0, 1.0, 2.0]), np.array([0.0, 4.0])),
            exponent=-1.0,
            expected_result=ZeroDivisionError,
            match="Zero densities cannot be raised to negative powers",
            test_id="histogram_base_scalar_exponent_with_zero_density_raises",
        ),
        TestCase(
            base=Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0])),
            exponent=Histogram(np.array([0.0, 1.0, 2.0]), np.array([-2.0, -4.0])),
            expected_result=None,
            test_id="histogram_base_histogram_exponent_valid",
        ),
        TestCase(
            base=Histogram(np.array([0.0, 1.0, 2.0]), np.array([0.0, 4.0])),
            exponent=Histogram(np.array([0.0, 1.0, 2.0]), np.array([-2.0, 2.0])),
            expected_result=ZeroDivisionError,
            match="Zero densities cannot be raised to negative powers",
            test_id="histogram_base_histogram_exponent_zero_density_negative_exponent_raises",
        ),
        TestCase(
            base=2.0,
            exponent=Histogram(np.array([0.0, 1.0, 2.0]), np.array([-2.0, -4.0])),
            expected_result=None,
            test_id="scalar_base_histogram_exponent_valid",
        ),
        TestCase(
            base=np.array([1.0, 2.0]),
            exponent=Histogram(np.array([0.0, 1.0, 2.0]), np.array([-2.0, -4.0])),
            expected_result=None,
            test_id="array_base_histogram_exponent_valid",
        ),
        TestCase(
            base="invalid",
            exponent=2.0,
            expected_result=TypeError,
            match="Unsupported base type",
            test_id="unsupported_base_type_raises",
        ),
        TestCase(
            base=2.0,
            exponent="invalid",
            expected_result=TypeError,
            match="Unsupported exponent type",
            test_id="unsupported_exponent_type_raises",
        ),
        TestCase(
            base=np.array([1.0, 2.0, 3.0]),
            exponent=xp.array([1.0, 2.0, 3.0]),
            expected_result=TypeError,
            match="Base and exponent must be of the same array type",
            test_id="mismatched_array_modules_raises",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.test_id)
    def test_validate_negative_power(self, test_case: TestCase) -> None:
        expect_error(
            Histogram._validate_negative_power,
            test_case.expected_result,
            test_case.base,
            test_case.exponent,
            match=test_case.match,
        )


class TestGetModule:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        obj: Union[Histogram, Array, Numeric]
        expected_module: ModuleType

    test_cases = [
        TestCase(
            obj=Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
            expected_module=np,
            test_id="histogram_numpy_returns_numpy",
        ),
        TestCase(
            obj=np.array([1.0, 2.0, 3.0]),
            expected_module=np,
            test_id="numpy_array_returns_numpy",
        ),
        TestCase(
            obj=xp.array([1.0, 2.0, 3.0]),
            expected_module=xp,
            test_id="cupy_array_returns_cupy",
        ),
        TestCase(
            obj=np.float64(3.14),
            expected_module=np,
            test_id="numpy_scalar_returns_numpy",
        ),
        TestCase(
            obj=3.14,
            expected_module=np,
            test_id="python_float_returns_numpy",
        ),
        TestCase(
            obj=42,
            expected_module=np,
            test_id="python_int_returns_numpy",
        ),
        TestCase(
            obj=Histogram(xp.array([0.0, 1.0, 2.0]), xp.array([1.0, 2.0])),
            expected_module=xp,
            test_id="histogram_cupy_returns_cupy",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.test_id)
    def test_get_module(self, test_case: TestCase) -> None:
        module = Histogram.get_module(test_case.obj)
        assert module is test_case.expected_module


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


class TestToCupy:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        histogram: Histogram
        expected_edges: Array
        expected_values: Array

    test_cases = [
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
            expected_edges=xp.array([0.0, 1.0, 2.0]),
            expected_values=xp.array([1.0, 2.0]),
            test_id="numpy_histogram_converts_to_cupy",
        ),
        TestCase(
            histogram=Histogram(xp.array([0.0, 1.0, 2.0]), xp.array([1.0, 2.0])),
            expected_edges=xp.array([0.0, 1.0, 2.0]),
            expected_values=xp.array([1.0, 2.0]),
            test_id="cupy_histogram_remains_cupy",
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 2.0, 3.0, 4.0]), np.array([2.0, 4.0, 6.0, 8.0])),
            expected_edges=xp.array([0.0, 1.0, 2.0, 3.0, 4.0]),
            expected_values=xp.array([2.0, 4.0, 6.0, 8.0]),
            test_id="larger_numpy_histogram_converts_to_cupy",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.test_id)
    def test_to_cupy(self, test_case: TestCase) -> None:
        cupy_histogram = test_case.histogram.to_cupy()
        assert type(cupy_histogram.edges).__module__.startswith("cupy")
        assert type(cupy_histogram.values).__module__.startswith("cupy")
        assert_array_equal(cupy_histogram.edges, test_case.expected_edges)
        assert_array_equal(cupy_histogram.values, test_case.expected_values)


class TestDensityToValues:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        edges: Union[Array, Histogram, Any]
        density: Union[Numeric, Array]
        expected_result: Union[Array, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            edges=Histogram(np.array([0.0, 2.0, 5.0]), np.array([4.0, 9.0])),
            density=3.0,
            expected_result=np.array([6.0, 9.0]),
            test_id="histogram_with_scalar_density",
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 4.0]),
            density=2.0,
            expected_result=np.array([2.0, 6.0]),
            test_id="array_edges_with_scalar_density",
        ),
        TestCase(
            edges=np.array([0.0, 1.0, 3.0, 6.0]),
            density=np.array([1.0, 2.0, 3.0]),
            expected_result=np.array([1.0, 4.0, 9.0]),
            test_id="array_edges_with_array_density",
        ),
        TestCase(
            edges=Histogram(np.array([0.0, 1.0, 3.0]), np.array([2.0, 4.0])),
            density=np.array([2.0, 3.0]),
            expected_result=np.array([2.0, 6.0]),
            test_id="histogram_with_array_density",
        ),
        TestCase(
            edges=xp.array([0.0, 2.0, 5.0]),
            density=4.0,
            expected_result=xp.array([8.0, 12.0]),
            test_id="cupy_array_edges_with_scalar_density",
        ),
        TestCase(
            edges="invalid",
            density=2.0,
            expected_result=TypeError,
            match="edges must be an Array or Histogram",
            test_id="invalid_edges_type_raises",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.test_id)
    def test_density_to_values(self, test_case: TestCase) -> None:
        if not expect_error(
            Histogram.density_to_values,
            test_case.expected_result,
            test_case.edges,
            test_case.density,
            match=test_case.match,
        ):
            values = Histogram.density_to_values(test_case.edges, test_case.density)
            assert_array_equal(values, test_case.expected_result)


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

    def test_rebin_invalid_type(self) -> None:
        histogram = Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0]))
        with pytest.raises(TypeError, match="Unsupported target_bins"):
            histogram.rebin("invalid")


class TestStaticRebin:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        histogram: Histogram
        target_bins: Union[Array, Any]
        expected_result: Union[Histogram, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0])),
            target_bins=np.array([0.0, 2.0]),
            expected_result=Histogram(np.array([0.0, 2.0]), np.array([6.0])),
            test_id="valid_rebin_combines_two_bins",
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 2.0, 3.0, 4.0]), np.array([1.0, 2.0, 3.0, 4.0])),
            target_bins=np.array([0.0, 2.0, 4.0]),
            expected_result=Histogram(np.array([0.0, 2.0, 4.0]), np.array([3.0, 7.0])),
            test_id="valid_rebin_combines_multiple_bins",
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 2.0, 3.0]), np.array([5.0, 10.0, 15.0])),
            target_bins=np.array([0.0, 3.0]),
            expected_result=Histogram(np.array([0.0, 3.0]), np.array([30.0])),
            test_id="valid_rebin_combines_all_bins",
        ),
        TestCase(
            histogram=Histogram(xp.array([0.0, 1.0, 2.0]), xp.array([2.0, 4.0])),
            target_bins=xp.array([0.0, 2.0]),
            expected_result=Histogram(xp.array([0.0, 2.0]), xp.array([6.0])),
            test_id="valid_rebin_cupy_arrays",
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0])),
            target_bins="invalid",
            expected_result=TypeError,
            match="target_bins must be an Array",
            test_id="invalid_target_bins_type_raises",
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0])),
            target_bins=np.array([0.0, 2.0, 1.5]),
            expected_result=ValueError,
            match="strictly increasing",
            test_id="not_strictly_increasing_raises",
        ),
        TestCase(
            histogram=Histogram(np.array([0.0, 1.0, 2.0, 3.0]), np.array([2.0, 4.0, 6.0])),
            target_bins=np.array([0.0, 1.0, 1.0, 3.0]),
            expected_result=ValueError,
            match="strictly increasing",
            test_id="duplicate_values_raises",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.test_id)
    def test_static_rebin(self, test_case: TestCase) -> None:
        if not expect_error(
            Histogram._rebin,
            test_case.expected_result,
            test_case.histogram,
            test_case.target_bins,
            match=test_case.match,
        ):
            rebinned = Histogram._rebin(test_case.histogram, test_case.target_bins)
            assert_array_equal(rebinned.edges, test_case.expected_result.edges)
            assert_array_equal(rebinned.values, test_case.expected_result.values)


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

        test_id: str
        histograms: Tuple[Histogram, ...]
        expected_result: Union[Array, Type[Exception]]
        match: Optional[str] = None

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
            expected_result=np.array([10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0]),
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
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        function: Any
        histograms: Tuple[Histogram, ...]
        expected_densities: Union[Array, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            function=lambda d: d**2,
            histograms=(Histogram(np.array([0.0, 1.0, 4.0]), np.array([2.0, 6.0])),),
            expected_densities=np.array([4.0, 4.0]),
            test_id="single_histogram_square",
        ),
        TestCase(
            function=lambda d: d + 5.0,
            histograms=(Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),),
            expected_densities=np.array([6.0, 7.0]),
            test_id="single_histogram_add_constant",
        ),
        TestCase(
            function=lambda d: d * 3.0,
            histograms=(Histogram(np.array([0.0, 1.0, 4.0]), np.array([2.0, 6.0])),),
            expected_densities=np.array([6.0, 6.0]),
            test_id="single_histogram_multiply_constant",
        ),
        TestCase(
            function=np.log,
            histograms=(Histogram(np.array([0.0, 1.0, 4.0]), np.array([np.e, 3 * np.e])),),
            expected_densities=np.array([1.0, 1.0]),
            test_id="single_histogram_log",
        ),
        TestCase(
            function=np.exp,
            histograms=(Histogram(np.array([0.0, 1.0, 4.0]), np.array([1.0, 3.0])),),
            expected_densities=np.array([np.e, np.e]),
            test_id="single_histogram_exp",
        ),
        TestCase(
            function=lambda d1, d2: d1 + d2,
            histograms=(
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0])),
            ),
            expected_densities=np.array([3.0, 6.0]),
            test_id="two_histograms_add",
        ),
        TestCase(
            function=lambda d1, d2: d1 * d2,
            histograms=(
                Histogram(np.array([0.0, 2.0, 8.0], dtype=np.float32), np.array([4.0, 12.0], dtype=np.float32)),
                Histogram(np.array([0.0, 2.0, 8.0], dtype=np.float32), np.array([6.0, 18.0], dtype=np.float32)),
            ),
            expected_densities=np.array([6.0, 6.0], dtype=np.float32),
            test_id="two_histograms_multiply",
        ),
        TestCase(
            function=lambda d1, d2, d3: d1 + d2 + d3,
            histograms=(
                Histogram(np.array([0.0, 2.0, 8.0]), np.array([2.0, 6.0])),
                Histogram(np.array([0.0, 2.0, 8.0]), np.array([4.0, 12.0])),
                Histogram(np.array([0.0, 2.0, 8.0]), np.array([6.0, 18.0])),
            ),
            expected_densities=np.array([6.0, 6.0]),
            test_id="three_histograms_add",
        ),
        TestCase(
            function=lambda d1, d2, d3, d4: d1 * d2 * d3 * d4,
            histograms=(
                Histogram(np.array([0.0, 2.0, 8.0]), np.array([4.0, 12.0])),
                Histogram(np.array([0.0, 2.0, 8.0]), np.array([2.0, 6.0])),
                Histogram(np.array([0.0, 2.0, 8.0]), np.array([6.0, 6.0])),
                Histogram(np.array([0.0, 2.0, 8.0]), np.array([2.0, 12.0])),
            ),
            expected_densities=np.array([6.0, 4.0]),
            test_id="four_histograms_multiply",
        ),
        TestCase(
            function=lambda d1, d2: d1 + d2,
            histograms=(
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
                Histogram(np.array([0.0, 1.0, 3.0]), np.array([2.0, 4.0])),
            ),
            expected_densities=ValueError,
            match="same edges",
            test_id="mismatched_edges_error",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.test_id,
    )
    def test_apply(self, test_case: TestCase) -> None:
        if not expect_error(
            Histogram.apply,
            test_case.expected_densities,
            test_case.function,
            *test_case.histograms,
            match=test_case.match,
        ):
            result = Histogram.apply(test_case.function, *test_case.histograms)
            assert_array_equal(result.densities, test_case.expected_densities)


class TestApplyWith:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        function: Any
        histogram: Histogram
        other_histograms: Tuple[Histogram, ...]
        expected_densities: Union[Array, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            function=lambda d1, d2: d1 * d2,
            histogram=Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
            other_histograms=(Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0])),),
            expected_densities=np.array([2.0, 8.0]),
            test_id="multiply_two_histograms",
        ),
        TestCase(
            function=lambda d1, d2: d1 + d2,
            histogram=Histogram(np.array([0.0, 2.0, 10.0], dtype=np.float32), np.array([4.0, 16.0], dtype=np.float32)),
            other_histograms=(
                Histogram(np.array([0.0, 2.0, 10.0], dtype=np.float32), np.array([6.0, 24.0], dtype=np.float32)),
            ),
            expected_densities=np.array([5.0, 5.0], dtype=np.float32),
            test_id="add_two_histograms",
        ),
        TestCase(
            function=lambda d1, d2, d3: d1 + d2 - d3,
            histogram=Histogram(np.array([0.0, 4.0, 8.0]), np.array([20.0, 24.0])),
            other_histograms=(
                Histogram(np.array([0.0, 4.0, 8.0]), np.array([12.0, 16.0])),
                Histogram(np.array([0.0, 4.0, 8.0]), np.array([8.0, 12.0])),
            ),
            expected_densities=np.array([6.0, 7.0]),
            test_id="three_histograms_combined",
        ),
        TestCase(
            function=lambda d1, d2: d1 / d2,
            histogram=Histogram(np.array([0.0, 2.0, 8.0]), np.array([12.0, 36.0])),
            other_histograms=(Histogram(np.array([0.0, 2.0, 8.0]), np.array([4.0, 12.0])),),
            expected_densities=np.array([3.0, 3.0]),
            test_id="divide_two_histograms",
        ),
        TestCase(
            function=lambda d1, d2: d1 + d2,
            histogram=Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
            other_histograms=(Histogram(np.array([0.0, 1.0, 3.0]), np.array([2.0, 4.0])),),
            expected_densities=ValueError,
            match="same edges",
            test_id="mismatched_edges_error",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.test_id,
    )
    def test_apply_with(self, test_case: TestCase) -> None:
        if not expect_error(
            test_case.histogram.apply_with,
            test_case.expected_densities,
            test_case.function,
            *test_case.other_histograms,
            match=test_case.match,
        ):
            result = test_case.histogram.apply_with(test_case.function, *test_case.other_histograms)
            assert_array_equal(result.densities, test_case.expected_densities)


class TestReduce:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        function: Any
        histograms: Tuple[Histogram, ...]
        expected_densities: Union[Array, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            function=np.add,
            histograms=(Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),),
            expected_densities=np.array([1.0, 2.0]),
            test_id="single_histogram_returns_same",
        ),
        TestCase(
            function=np.add,
            histograms=(
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0])),
            ),
            expected_densities=np.array([3.0, 6.0]),
            test_id="two_histograms_add",
        ),
        TestCase(
            function=np.multiply,
            histograms=(
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0])),
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([3.0, 6.0])),
            ),
            expected_densities=np.array([6.0, 24.0]),
            test_id="two_histograms_multiply",
        ),
        TestCase(
            function=np.add,
            histograms=(
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0])),
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([3.0, 6.0])),
            ),
            expected_densities=np.array([6.0, 12.0]),
            test_id="three_histograms_add",
        ),
        TestCase(
            function=np.multiply,
            histograms=(
                Histogram(np.array([0.0, 4.0, 8.0], dtype=np.float32), np.array([8.0, 12.0], dtype=np.float32)),
                Histogram(np.array([0.0, 4.0, 8.0], dtype=np.float32), np.array([12.0, 8.0], dtype=np.float32)),
                Histogram(np.array([0.0, 4.0, 8.0], dtype=np.float32), np.array([8.0, 12.0], dtype=np.float32)),
            ),
            expected_densities=np.array([12.0, 18.0], dtype=np.float32),
            test_id="three_histograms_multiply",
        ),
        TestCase(
            function=np.add,
            histograms=(
                Histogram(np.array([0.0, 2.0, 10.0]), np.array([2.0, 8.0])),
                Histogram(np.array([0.0, 2.0, 10.0]), np.array([4.0, 16.0])),
                Histogram(np.array([0.0, 2.0, 10.0]), np.array([6.0, 24.0])),
                Histogram(np.array([0.0, 2.0, 10.0]), np.array([8.0, 32.0])),
            ),
            expected_densities=np.array([10.0, 10.0]),
            test_id="four_histograms_add",
        ),
        TestCase(
            function=np.maximum,
            histograms=(
                Histogram(np.array([0.0, 2.0, 8.0]), np.array([4.0, 10.0])),
                Histogram(np.array([0.0, 2.0, 8.0]), np.array([6.0, 12.0])),
                Histogram(np.array([0.0, 2.0, 8.0]), np.array([2.0, 18.0])),
            ),
            expected_densities=np.array([3.0, 3.0]),
            test_id="three_histograms_maximum",
        ),
        TestCase(
            function=np.add,
            histograms=(
                Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
                Histogram(np.array([0.0, 1.0, 3.0]), np.array([2.0, 4.0])),
            ),
            expected_densities=ValueError,
            match="same edges",
            test_id="mismatched_edges_error",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.test_id,
    )
    def test_reduce(self, test_case: TestCase) -> None:
        if not expect_error(
            Histogram.reduce,
            test_case.expected_densities,
            test_case.function,
            *test_case.histograms,
            match=test_case.match,
        ):
            result = Histogram.reduce(test_case.function, *test_case.histograms)
            assert_array_equal(result.densities, test_case.expected_densities)


class TestReduceWith:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        function: Any
        histogram: Histogram
        other_histograms: Tuple[Histogram, ...]
        expected_densities: Union[Array, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            function=np.multiply,
            histogram=Histogram(np.array([0.0, 1.0, 2.0]), np.array([2.0, 4.0])),
            other_histograms=(Histogram(np.array([0.0, 1.0, 2.0]), np.array([3.0, 6.0])),),
            expected_densities=np.array([6.0, 24.0]),
            test_id="multiply_two_histograms",
        ),
        TestCase(
            function=np.add,
            histogram=Histogram(np.array([0.0, 2.0, 10.0], dtype=np.float32), np.array([2.0, 8.0], dtype=np.float32)),
            other_histograms=(
                Histogram(np.array([0.0, 2.0, 10.0], dtype=np.float32), np.array([6.0, 24.0], dtype=np.float32)),
            ),
            expected_densities=np.array([4.0, 4.0], dtype=np.float32),
            test_id="add_two_histograms",
        ),
        TestCase(
            function=np.add,
            histogram=Histogram(np.array([0.0, 4.0, 8.0]), np.array([4.0, 8.0])),
            other_histograms=(
                Histogram(np.array([0.0, 4.0, 8.0]), np.array([8.0, 12.0])),
                Histogram(np.array([0.0, 4.0, 8.0]), np.array([12.0, 16.0])),
            ),
            expected_densities=np.array([6.0, 9.0]),
            test_id="add_three_histograms",
        ),
        TestCase(
            function=np.minimum,
            histogram=Histogram(np.array([0.0, 2.0, 8.0]), np.array([10.0, 18.0])),
            other_histograms=(
                Histogram(np.array([0.0, 2.0, 8.0]), np.array([6.0, 24.0])),
                Histogram(np.array([0.0, 2.0, 8.0]), np.array([8.0, 12.0])),
            ),
            expected_densities=np.array([3.0, 2.0]),
            test_id="minimum_three_histograms",
        ),
        TestCase(
            function=np.add,
            histogram=Histogram(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0])),
            other_histograms=(Histogram(np.array([0.0, 1.0, 3.0]), np.array([2.0, 4.0])),),
            expected_densities=ValueError,
            match="same edges",
            test_id="mismatched_edges_error",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.test_id,
    )
    def test_reduce_with(self, test_case: TestCase) -> None:
        if not expect_error(
            test_case.histogram.reduce_with,
            test_case.expected_densities,
            test_case.function,
            *test_case.other_histograms,
            match=test_case.match,
        ):
            result = test_case.histogram.reduce_with(test_case.function, *test_case.other_histograms)
            assert_array_equal(result.densities, test_case.expected_densities)


class TestAddition:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        left: Union[Histogram, Array, Numeric]
        right: Union[Histogram, Array, Numeric]
        expected_result: Union[Histogram, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 7.0]), np.array([4.0, 15.0])),
            right=Histogram(np.array([0.0, 2.0, 7.0]), np.array([6.0, 20.0])),
            expected_result=Histogram(np.array([0.0, 2.0, 7.0]), np.array([10.0, 35.0])),
            test_id="two_histograms_same_edges",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 8.0, 12.0]), np.array([9.0, 15.0, 16.0])),
            right=Histogram(np.array([0.0, 3.0, 6.0, 10.0]), np.array([6.0, 12.0, 20.0])),
            expected_result=Histogram(
                np.array([0.0, 3.0, 6.0, 8.0, 10.0, 12.0]), np.array([15.0, 21.0, 16.0, 18.0, 8.0])
            ),
            test_id="two_histograms_overlapping_common_edges",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 4.0, 10.0]), np.array([8.0, 18.0])),
            right=Histogram(np.array([2.0, 6.0, 8.0, 12.0]), np.array([8.0, 10.0, 16.0])),
            expected_result=Histogram(
                np.array([0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0]), np.array([4.0, 8.0, 10.0, 16.0, 14.0, 8.0])
            ),
            test_id="two_histograms_overlapping_no_common_edges",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 4.0, 8.0]), np.array([8.0, 16.0])),
            right=Histogram(np.array([10.0, 15.0, 20.0]), np.array([10.0, 25.0])),
            expected_result=Histogram(
                np.array([0.0, 4.0, 8.0, 10.0, 15.0, 20.0]), np.array([8.0, 16.0, 0.0, 10.0, 25.0])
            ),
            test_id="two_histograms_disjoint",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 10.0], dtype=np.float32), np.array([4.0, 16.0], dtype=np.float32)),
            right=Histogram(np.array([0.0, 2.0, 10.0], dtype=np.float32), np.array([6.0, 24.0], dtype=np.float32)),
            expected_result=Histogram(
                np.array([0.0, 2.0, 10.0], dtype=np.float32), np.array([10.0, 40.0], dtype=np.float32)
            ),
            test_id="two_histograms_float32",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 8.0]), np.array([0.0, 0.0])),
            right=Histogram(np.array([0.0, 3.0, 8.0]), np.array([6.0, 15.0])),
            expected_result=Histogram(np.array([0.0, 3.0, 8.0]), np.array([6.0, 15.0])),
            test_id="zero_histogram_plus_histogram",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 10.0]), np.array([6.0, 21.0])),
            right=3.0,
            expected_result=Histogram(np.array([0.0, 3.0, 10.0]), np.array([15.0, 42.0])),
            test_id="histogram_plus_scalar",
        ),
        TestCase(
            left=3.0,
            right=Histogram(np.array([0.0, 3.0, 10.0]), np.array([6.0, 21.0])),
            expected_result=Histogram(np.array([0.0, 3.0, 10.0]), np.array([15.0, 42.0])),
            test_id="scalar_plus_histogram",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 7.0]), np.array([4.0, 15.0])),
            right=np.array([2.0, 3.0]),
            expected_result=Histogram(np.array([0.0, 2.0, 7.0]), np.array([6.0, 18.0])),
            test_id="histogram_plus_array",
        ),
        TestCase(
            left=np.array([2.0, 3.0]),
            right=Histogram(np.array([0.0, 2.0, 7.0]), np.array([4.0, 15.0])),
            expected_result=Histogram(np.array([0.0, 2.0, 7.0]), np.array([6.0, 18.0])),
            test_id="array_plus_histogram",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 8.0]), np.array([6.0, 15.0])),
            right=np.array([0.0, 0.0]),
            expected_result=Histogram(np.array([0.0, 3.0, 8.0]), np.array([6.0, 15.0])),
            test_id="histogram_plus_zero_array",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 7.0]), np.array([4.0, 15.0])),
            right=np.array([2.0, 3.0, 4.0]),
            expected_result=ValueError,
            match="must match",
            test_id="array_wrong_length_error",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 7.0]), np.array([4.0, 15.0])),
            right="invalid",
            expected_result=TypeError,
            match="Unsupported type for addition",
            test_id="invalid_type_error",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.test_id,
    )
    def test_addition(self, test_case: TestCase) -> None:
        if not expect_error(lambda: test_case.left + test_case.right, test_case.expected_result, match=test_case.match):
            result = test_case.left + test_case.right
            assert isinstance(test_case.expected_result, Histogram)
            assert isinstance(result, Histogram)
            assert_array_equal(result.edges, test_case.expected_result.edges)
            assert_array_equal(result.values, test_case.expected_result.values)


class TestSubtraction:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        left: Union[Histogram, Array, Numeric]
        right: Union[Histogram, Array, Numeric]
        expected_result: Union[Histogram, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 7.0]), np.array([10.0, 25.0])),
            right=Histogram(np.array([0.0, 2.0, 7.0]), np.array([4.0, 10.0])),
            expected_result=Histogram(np.array([0.0, 2.0, 7.0]), np.array([6.0, 15.0])),
            test_id="two_histograms_same_edges",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 8.0, 12.0]), np.array([15.0, 20.0, 24.0])),
            right=Histogram(np.array([0.0, 3.0, 6.0, 10.0]), np.array([9.0, 12.0, 16.0])),
            expected_result=Histogram(np.array([0.0, 3.0, 6.0, 8.0, 10.0, 12.0]), np.array([6.0, 0.0, 0.0, 4.0, 12.0])),
            test_id="two_histograms_overlapping_common_edges",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 4.0, 10.0]), np.array([12.0, 24.0])),
            right=Histogram(np.array([2.0, 6.0, 8.0, 12.0]), np.array([8.0, 10.0, 16.0])),
            expected_result=Histogram(
                np.array([0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0]), np.array([6.0, 2.0, 4.0, -2.0, 0.0, -8.0])
            ),
            test_id="two_histograms_overlapping_no_common_edges",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 4.0, 8.0]), np.array([8.0, 16.0])),
            right=Histogram(np.array([10.0, 15.0, 20.0]), np.array([10.0, 25.0])),
            expected_result=Histogram(
                np.array([0.0, 4.0, 8.0, 10.0, 15.0, 20.0]), np.array([8.0, 16.0, 0.0, -10.0, -25.0])
            ),
            test_id="two_histograms_disjoint",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 4.0, 8.0], dtype=np.float32), np.array([16.0, 20.0], dtype=np.float32)),
            right=Histogram(np.array([0.0, 4.0, 8.0], dtype=np.float32), np.array([8.0, 12.0], dtype=np.float32)),
            expected_result=Histogram(
                np.array([0.0, 4.0, 8.0], dtype=np.float32), np.array([8.0, 8.0], dtype=np.float32)
            ),
            test_id="two_histograms_float32",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 8.0]), np.array([9.0, 20.0])),
            right=Histogram(np.array([0.0, 3.0, 8.0]), np.array([0.0, 0.0])),
            expected_result=Histogram(np.array([0.0, 3.0, 8.0]), np.array([9.0, 20.0])),
            test_id="histogram_minus_zero_histogram",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 10.0]), np.array([9.0, 28.0])),
            right=2.0,
            expected_result=Histogram(np.array([0.0, 3.0, 10.0]), np.array([3.0, 14.0])),
            test_id="histogram_minus_scalar",
        ),
        TestCase(
            left=10.0,
            right=Histogram(np.array([0.0, 3.0, 10.0]), np.array([6.0, 21.0])),
            expected_result=Histogram(np.array([0.0, 3.0, 10.0]), np.array([24.0, 49.0])),
            test_id="scalar_minus_histogram",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 7.0]), np.array([8.0, 20.0])),
            right=np.array([2.0, 3.0]),
            expected_result=Histogram(np.array([0.0, 2.0, 7.0]), np.array([6.0, 17.0])),
            test_id="histogram_minus_array",
        ),
        TestCase(
            left=np.array([10.0, 25.0]),
            right=Histogram(np.array([0.0, 2.0, 7.0]), np.array([4.0, 15.0])),
            expected_result=Histogram(np.array([0.0, 2.0, 7.0]), np.array([6.0, 10.0])),
            test_id="array_minus_histogram",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.test_id,
    )
    def test_subtraction(self, test_case: TestCase) -> None:
        if not expect_error(lambda: test_case.left - test_case.right, test_case.expected_result, match=test_case.match):
            result = test_case.left - test_case.right
            assert isinstance(test_case.expected_result, Histogram)
            assert isinstance(result, Histogram)
            assert_array_equal(result.edges, test_case.expected_result.edges)
            assert_array_equal(result.values, test_case.expected_result.values)


class TestMultiplication:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        left: Union[Histogram, Array, Numeric]
        right: Union[Histogram, Array, Numeric]
        expected_result: Union[Histogram, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 7.0]), np.array([4.0, 15.0])),
            right=Histogram(np.array([0.0, 2.0, 7.0]), np.array([6.0, 20.0])),
            expected_result=Histogram(np.array([0.0, 2.0, 7.0]), np.array([12.0, 60.0])),
            test_id="two_histograms_same_edges",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 8.0, 12.0]), np.array([6.0, 10.0, 16.0])),
            right=Histogram(np.array([0.0, 3.0, 6.0, 10.0]), np.array([4.0, 12.0, 20.0])),
            expected_result=Histogram(
                np.array([0.0, 3.0, 6.0, 8.0, 10.0, 12.0]), np.array([8.0, 24.0, 20.0, 40.0, 0.0])
            ),
            test_id="two_histograms_overlapping_common_edges",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 4.0, 10.0]), np.array([8.0, 18.0])),
            right=Histogram(np.array([2.0, 6.0, 8.0, 12.0]), np.array([8.0, 10.0, 16.0])),
            expected_result=Histogram(
                np.array([0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0]), np.array([0.0, 8.0, 12.0, 30.0, 24.0, 0.0])
            ),
            test_id="two_histograms_overlapping_no_common_edges",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 4.0, 8.0]), np.array([8.0, 16.0])),
            right=Histogram(np.array([10.0, 15.0, 20.0]), np.array([10.0, 25.0])),
            expected_result=Histogram(np.array([0.0, 4.0, 8.0, 10.0, 15.0, 20.0]), np.array([0.0, 0.0, 0.0, 0.0, 0.0])),
            test_id="two_histograms_disjoint",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 4.0, 8.0], dtype=np.float32), np.array([8.0, 12.0], dtype=np.float32)),
            right=Histogram(np.array([0.0, 4.0, 8.0], dtype=np.float32), np.array([12.0, 8.0], dtype=np.float32)),
            expected_result=Histogram(
                np.array([0.0, 4.0, 8.0], dtype=np.float32), np.array([24.0, 24.0], dtype=np.float32)
            ),
            test_id="two_histograms_float32",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 8.0]), np.array([0.0, 0.0])),
            right=Histogram(np.array([0.0, 3.0, 8.0]), np.array([6.0, 15.0])),
            expected_result=Histogram(np.array([0.0, 3.0, 8.0]), np.array([0.0, 0.0])),
            test_id="zero_histogram_times_histogram",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 10.0]), np.array([6.0, 21.0])),
            right=3.0,
            expected_result=Histogram(np.array([0.0, 3.0, 10.0]), np.array([18.0, 63.0])),
            test_id="histogram_times_scalar",
        ),
        TestCase(
            left=3.0,
            right=Histogram(np.array([0.0, 3.0, 10.0]), np.array([6.0, 21.0])),
            expected_result=Histogram(np.array([0.0, 3.0, 10.0]), np.array([18.0, 63.0])),
            test_id="scalar_times_histogram",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 7.0]), np.array([4.0, 15.0])),
            right=np.array([2.0, 3.0]),
            expected_result=Histogram(np.array([0.0, 2.0, 7.0]), np.array([4.0, 9.0])),
            test_id="histogram_times_array",
        ),
        TestCase(
            left=np.array([2.0, 3.0]),
            right=Histogram(np.array([0.0, 2.0, 7.0]), np.array([4.0, 15.0])),
            expected_result=Histogram(np.array([0.0, 2.0, 7.0]), np.array([4.0, 9.0])),
            test_id="array_times_histogram",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 8.0]), np.array([6.0, 15.0])),
            right=np.array([0.0, 1.0]),
            expected_result=Histogram(np.array([0.0, 3.0, 8.0]), np.array([0.0, 3.0])),
            test_id="histogram_times_array_with_zero",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 7.0]), np.array([4.0, 15.0])),
            right=np.array([2.0, 3.0, 4.0]),
            expected_result=ValueError,
            match="must match",
            test_id="array_wrong_length_error",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 7.0]), np.array([4.0, 15.0])),
            right="invalid",
            expected_result=TypeError,
            match="Unsupported type for multiplication",
            test_id="invalid_type_error",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.test_id,
    )
    def test_multiplication(self, test_case: TestCase) -> None:
        if not expect_error(lambda: test_case.left * test_case.right, test_case.expected_result, match=test_case.match):
            result = test_case.left * test_case.right
            assert isinstance(test_case.expected_result, Histogram)
            assert isinstance(result, Histogram)
            assert_array_equal(result.edges, test_case.expected_result.edges)
            assert_array_equal(result.values, test_case.expected_result.values)


class TestDivision:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        left: Union[Histogram, Array, Numeric]
        right: Union[Histogram, Array, Numeric]
        expected_result: Union[Histogram, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 10.0]), np.array([12.0, 42.0])),
            right=2.0,
            expected_result=Histogram(np.array([0.0, 3.0, 10.0]), np.array([6.0, 21.0])),
            test_id="histogram_divided_by_scalar",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 7.0]), np.array([12.0, 45.0])),
            right=Histogram(np.array([0.0, 2.0, 7.0]), np.array([4.0, 15.0])),
            expected_result=Histogram(np.array([0.0, 2.0, 7.0]), np.array([6.0, 15.0])),
            test_id="histogram_divided_by_histogram_same_edges",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 8.0, 10.0]), np.array([18.0, 30.0, 48.0])),
            right=Histogram(np.array([0.0, 3.0, 6.0, 12.0]), np.array([6.0, 12.0, 20.0])),
            expected_result=Histogram(np.array([0.0, 3.0, 6.0, 8.0, 10.0, 12.0]), np.array([9.0, 4.5, 3.6, 14.4, 0.0])),
            test_id="histogram_divided_by_histogram_containing_common_edges",
        ),
        TestCase(
            left=Histogram(np.array([2.0, 3.0, 4.0]), np.array([16.0, 36.0])),
            right=Histogram(np.array([0.0, 6.0, 8.0, 12.0]), np.array([8.0, 10.0, 16.0])),
            expected_result=Histogram(
                np.array([0.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0]), np.array([0.0, 12.0, 27.0, 0.0, 0.0, 0.0])
            ),
            test_id="histogram_divided_by_histogram_containing_no_common_edges",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 4.0, 10.0]), np.array([16.0, 36.0])),
            right=Histogram(np.array([2.0, 6.0, 8.0, 12.0]), np.array([8.0, 10.0, 16.0])),
            expected_result=ZeroDivisionError,
            test_id="histogram_divided_by_histogram_partially_overlapping",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 4.0, 8.0]), np.array([16.0, 24.0])),
            right=Histogram(np.array([10.0, 15.0, 20.0]), np.array([10.0, 25.0])),
            expected_result=ZeroDivisionError,
            test_id="histogram_divided_by_disjoint_histogram",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 4.0, 8.0], dtype=np.float32), np.array([24.0, 16.0], dtype=np.float32)),
            right=Histogram(np.array([0.0, 4.0, 8.0], dtype=np.float32), np.array([8.0, 16.0], dtype=np.float32)),
            expected_result=Histogram(
                np.array([0.0, 4.0, 8.0], dtype=np.float32), np.array([12.0, 4.0], dtype=np.float32)
            ),
            test_id="histogram_divided_by_histogram_float32",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 7.0]), np.array([12.0, 45.0])),
            right=Histogram(np.array([0.0, 2.0, 7.0]), np.array([0.0, 0.0])),
            expected_result=ZeroDivisionError,
            test_id="histogram_divided_by_zero_histogram",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 7.0]), np.array([12.0, 45.0])),
            right=np.array([2.0, 3.0]),
            expected_result=Histogram(np.array([0.0, 2.0, 7.0]), np.array([6.0, 15.0])),
            test_id="histogram_divided_by_array",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 8.0]), np.array([12.0, 30.0])),
            right=np.array([2.0, 0.0]),
            expected_result=ZeroDivisionError,
            test_id="histogram_divided_by_array_with_zero",
        ),
        TestCase(
            left=12.0,
            right=Histogram(np.array([0.0, 3.0, 4.0]), np.array([6.0, 12.0])),
            expected_result=Histogram(np.array([0.0, 3.0, 4.0]), np.array([18.0, 1.0])),
            test_id="scalar_divided_by_histogram",
        ),
        TestCase(
            left=12.0,
            right=Histogram(np.array([0.0, 3.0, 8.0]), np.array([0.0, 0.0])),
            expected_result=ZeroDivisionError,
            test_id="scalar_divided_by_zero_histogram",
        ),
        TestCase(
            left=np.array([12.0, 45.0]),
            right=Histogram(np.array([0.0, 2.0, 7.0]), np.array([4.0, 15.0])),
            expected_result=Histogram(np.array([0.0, 2.0, 7.0]), np.array([6.0, 15.0])),
            test_id="array_divided_by_histogram",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 7.0]), np.array([12.0, 45.0])),
            right=np.array([2.0, 3.0, 4.0]),
            expected_result=ValueError,
            match="must match",
            test_id="array_wrong_length_error",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 7.0]), np.array([12.0, 45.0])),
            right=0.0,
            expected_result=ZeroDivisionError,
            match="Division by zero scalar is not allowed",
            test_id="division_by_zero_scalar_error",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 7.0]), np.array([12.0, 45.0])),
            right="invalid",
            expected_result=TypeError,
            match="Unsupported type for division",
            test_id="invalid_type_error",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.test_id,
    )
    def test_division(self, test_case: TestCase) -> None:
        if not expect_error(lambda: test_case.left / test_case.right, test_case.expected_result, match=test_case.match):
            result = test_case.left / test_case.right
            assert isinstance(test_case.expected_result, Histogram)
            assert isinstance(result, Histogram)
            assert_array_equal(result.edges, test_case.expected_result.edges)
            assert_array_equal(result.values, test_case.expected_result.values)


class TestPower:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        left: Union[Histogram, Array, Numeric]
        right: Union[Histogram, Array, Numeric]
        expected_result: Union[Histogram, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 10.0]), np.array([6.0, 21.0])),
            right=2,
            expected_result=Histogram(np.array([0.0, 3.0, 10.0]), np.array([12.0, 63.0])),
            test_id="histogram_power_square",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 7.0]), np.array([4.0, 10.0])),
            right=3,
            expected_result=Histogram(np.array([0.0, 2.0, 7.0]), np.array([16.0, 40.0])),
            test_id="histogram_power_cube",
        ),
        TestCase(
            left=Histogram(np.array([2.0, 3.0, 5.0]), np.array([5.0, 2.0])),
            right=-1,
            expected_result=Histogram(np.array([2.0, 3.0, 5.0]), np.array([0.2, 2.0])),
            test_id="histogram_power_inverse",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 10.0]), np.array([12.0, 28.0])),
            right=0.5,
            expected_result=Histogram(np.array([0.0, 3.0, 10.0]), np.array([6.0, 14.0])),
            test_id="histogram_power_fractional",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 10.0]), np.array([6.0, 21.0])),
            right=0,
            expected_result=Histogram(np.array([0.0, 3.0, 10.0]), np.array([3.0, 7.0])),
            test_id="histogram_power_zero",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 10.0], dtype=np.float32), np.array([8.0, 24.0], dtype=np.float32)),
            right=2,
            expected_result=Histogram(
                np.array([0.0, 2.0, 10.0], dtype=np.float32), np.array([32.0, 72.0], dtype=np.float32)
            ),
            test_id="histogram_power_square_float32",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 10.0]), np.array([6.0, 21.0])),
            right=np.array([6.0, 7.0]),
            expected_result=Histogram(np.array([0.0, 3.0, 10.0]), np.array([12.0, 21.0])),
            test_id="histogram_power_array",
        ),
        TestCase(
            left=2.0,
            right=Histogram(np.array([0.0, 3.0, 10.0]), np.array([6.0, 21.0])),
            expected_result=Histogram(np.array([0.0, 3.0, 10.0]), np.array([12.0, 56.0])),
            test_id="scalar_power_histogram",
        ),
        TestCase(
            left=np.array([2.0, 50.0]),
            right=Histogram(np.array([-1.0, 0.0, 2.0]), np.array([4.0, -4.0])),
            expected_result=Histogram(np.array([-1.0, 0.0, 2.0]), np.array([16.0, 0.0032])),
            test_id="array_power_histogram",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 10.0]), np.array([6.0, 21.0])),
            right=np.array([2.0, 3.0, 4.0]),
            expected_result=ValueError,
            match="must match",
            test_id="array_wrong_length_error",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 10.0]), np.array([6.0, 21.0])),
            right=Histogram(np.array([0.0, 3.0, 10.0]), np.array([12.0, 14.0])),
            expected_result=Histogram(np.array([0.0, 3.0, 10.0]), np.array([48.0, 63.0])),
            test_id="histogram_power_histogram",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 10.0]), np.array([6.0, 21.0])),
            right="invalid",
            expected_result=TypeError,
            match="Unsupported type for power",
            test_id="invalid_type_pow_error",
        ),
        TestCase(
            left="invalid",
            right=Histogram(np.array([0.0, 3.0, 10.0]), np.array([6.0, 21.0])),
            expected_result=TypeError,
            match="Unsupported type for power",
            test_id="invalid_type_rpow_error",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 6.0, 10.0]), np.array([4.0, 8.0, 12.0])),
            right=Histogram(np.array([2.0, 4.0, 6.0]), np.array([2.0, 3.0])),
            expected_result=Histogram(
                np.array([0.0, 2.0, 4.0, 6.0, 10.0]), np.array([2.0, 4.0, 5.656854249492381, 4.0])
            ),
            test_id="exponent_range_strictly_contained_in_base_range",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 6.0, 10.0]), np.array([4.0, 8.0, 12.0])),
            right=Histogram(np.array([2.0, 4.0, 6.0]), np.array([-2.0, -3.0])),
            expected_result=Histogram(
                np.array([0.0, 2.0, 4.0, 6.0, 10.0]), np.array([2.0, 1.0, 0.7071067811865476, 4.0])
            ),
            test_id="exponent_range_strictly_contained_in_base_range_negative_exponents",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 6.0, 10.0]), np.array([4.0, 0.0, 12.0])),
            right=Histogram(np.array([2.0, 4.0, 6.0]), np.array([2.0, -3.0])),
            expected_result=ZeroDivisionError,
            match="Zero densities cannot be raised to negative powers",
            test_id="exponent_range_strictly_contained_in_base_range_zero_density_negative_exponent",
        ),
        TestCase(
            left=Histogram(np.array([2.0, 4.0, 6.0]), np.array([3.0, 5.0])),
            right=Histogram(np.array([0.0, 2.0, 6.0, 10.0]), np.array([2.0, 4.0, 3.0])),
            expected_result=Histogram(np.array([0.0, 2.0, 4.0, 6.0, 10.0]), np.array([0.0, 3.0, 5.0, 0.0])),
            test_id="base_range_strictly_contained_in_exponent_range",
        ),
        TestCase(
            left=Histogram(np.array([2.0, 4.0, 6.0]), np.array([3.0, 5.0])),
            right=Histogram(np.array([0.0, 2.0, 6.0, 10.0]), np.array([-2.0, -4.0, -3.0])),
            expected_result=ZeroDivisionError,
            match="Zero densities cannot be raised to negative powers",
            test_id="base_range_strictly_contained_in_exponent_range_negative_exponents",
        ),
        TestCase(
            left=Histogram(np.array([2.0, 4.0, 6.0]), np.array([0.0, 5.0])),
            right=Histogram(np.array([0.0, 2.0, 6.0, 10.0]), np.array([2.0, -4.0, 3.0])),
            expected_result=ZeroDivisionError,
            match="Zero densities cannot be raised to negative powers",
            test_id="base_range_strictly_contained_in_exponent_range_zero_density_negative_exponent",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 7.0, 10.0]), np.array([6.0, 8.0, 10.0])),
            right=Histogram(np.array([2.0, 5.0, 8.0, 12.0]), np.array([3.0, 6.0, 12.0])),
            expected_result=Histogram(
                np.array([0.0, 2.0, 3.0, 5.0, 7.0, 8.0, 10.0, 12.0]),
                np.array([2.0, 2.0, 4.0, 8.0, 11.11111111111111, 74.07407407407408, 0.0]),
            ),
            test_id="base_and_exponent_overlap_partially",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 7.0, 10.0]), np.array([6.0, 8.0, 10.0])),
            right=Histogram(np.array([2.0, 5.0, 8.0, 12.0]), np.array([-3.0, -6.0, -12.0])),
            expected_result=ZeroDivisionError,
            match="Zero densities cannot be raised to negative powers",
            test_id="base_and_exponent_overlap_partially_negative_exponents",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 3.0, 7.0, 10.0]), np.array([6.0, 0.0, 10.0])),
            right=Histogram(np.array([2.0, 5.0, 8.0, 12.0]), np.array([3.0, -6.0, 12.0])),
            expected_result=ZeroDivisionError,
            match="Zero densities cannot be raised to negative powers",
            test_id="base_and_exponent_overlap_partially_zero_density_negative_exponent",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 5.0]), np.array([4.0, 6.0])),
            right=Histogram(np.array([6.0, 8.0, 10.0]), np.array([2.0, 3.0])),
            expected_result=Histogram(np.array([0.0, 2.0, 5.0, 6.0, 8.0, 10.0]), np.array([2.0, 3.0, 1.0, 0.0, 0.0])),
            test_id="base_and_exponent_disjoint_ranges",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 5.0]), np.array([4.0, 6.0])),
            right=Histogram(np.array([6.0, 8.0, 10.0]), np.array([-2.0, -3.0])),
            expected_result=ZeroDivisionError,
            match="Zero densities cannot be raised to negative powers",
            test_id="base_and_exponent_disjoint_ranges_negative_exponents",
        ),
        TestCase(
            left=Histogram(np.array([0.0, 2.0, 5.0]), np.array([0.0, 6.0])),
            right=Histogram(np.array([6.0, 8.0, 10.0]), np.array([-2.0, 3.0])),
            expected_result=ZeroDivisionError,
            match="Zero densities cannot be raised to negative powers",
            test_id="base_and_exponent_disjoint_ranges_zero_density",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.test_id,
    )
    def test_power(self, test_case: TestCase) -> None:
        if not expect_error(lambda: test_case.left**test_case.right, test_case.expected_result, match=test_case.match):
            result = test_case.left**test_case.right
            assert isinstance(test_case.expected_result, Histogram)
            assert isinstance(result, Histogram)
            assert_array_equal(result.edges, test_case.expected_result.edges)
            assert_array_equal(result.values, test_case.expected_result.values)


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
