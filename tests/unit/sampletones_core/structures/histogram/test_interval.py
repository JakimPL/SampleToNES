from dataclasses import dataclass
from typing import List, Optional, Type, Union

import numpy as np
import pytest

from sampletones_core.structures.histogram.interval import Interval
from sampletones_shared.types.array import Float
from tests.suite.arrays import assert_array_equal
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase
from tests.suite.errors import expect_error


class TestBool(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: bool
        interval: Interval

        @property
        def label(self) -> str:
            return f"[{self.interval.left},{self.interval.right}]_expect_{self.expected}"

    test_cases = [
        TestCase(interval=Interval(0.0, 1.0), expected=True),
        TestCase(interval=Interval(1.0, 5.0), expected=True),
        TestCase(interval=Interval(-10.0, 10.0), expected=True),
        TestCase(interval=Interval(np.float32(0.0), np.float32(1.0)), expected=True),
        TestCase(interval=Interval(np.float64(5.5), np.float64(10.5)), expected=True),
        TestCase(interval=Interval(-np.inf, 0.0), expected=True),
        TestCase(interval=Interval(0.0, np.inf), expected=True),
        TestCase(interval=Interval(-np.inf, np.inf), expected=True),
        TestCase(interval=Interval(1.0, 1.0), expected=False),
        TestCase(interval=Interval(5.0, 5.0), expected=False),
        TestCase(interval=Interval(5.0, 3.0), expected=False),
        TestCase(interval=Interval(np.float32(2.0), np.float32(1.0)), expected=False),
        TestCase(
            interval=Interval(np.float64(10.0), np.float64(10.0)),
            expected=False,
        ),
        TestCase(interval=Interval(np.inf, np.inf), expected=False),
        TestCase(interval=Interval(np.inf, -np.inf), expected=False),
        TestCase(interval=Interval(np.nan, 1.0), expected=False),
        TestCase(interval=Interval(0.0, np.nan), expected=False),
        TestCase(interval=Interval(np.nan, np.nan), expected=False),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_bool(self, test_case: TestCase) -> None:
        assert bool(test_case.interval) == test_case.expected


class TestLength(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Float
        interval: Interval

        @property
        def label(self) -> str:
            return f"[{self.interval.left},{self.interval.right}]"

    test_cases = [
        TestCase(interval=Interval(0.0, 1.0), expected=1.0),
        TestCase(interval=Interval(0.0, 5.0), expected=5.0),
        TestCase(interval=Interval(2.0, 7.0), expected=5.0),
        TestCase(interval=Interval(-5.0, 5.0), expected=10.0),
        TestCase(
            interval=Interval(np.float32(1.5), np.float32(3.5)),
            expected=np.float32(2.0),
        ),
        TestCase(
            interval=Interval(np.float64(10.0), np.float64(15.0)),
            expected=np.float64(5.0),
        ),
        TestCase(interval=Interval(-np.inf, 0.0), expected=np.inf),
        TestCase(interval=Interval(0.0, np.inf), expected=np.inf),
        TestCase(interval=Interval(-np.inf, np.inf), expected=np.inf),
        TestCase(interval=Interval(1.0, 1.0), expected=0.0),
        TestCase(interval=Interval(5.0, 3.0), expected=0.0),
        TestCase(
            interval=Interval(np.float32(10.0), np.float32(5.0)),
            expected=np.float32(0.0),
        ),
        TestCase(interval=Interval(np.inf, np.inf), expected=0.0),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_length(self, test_case: TestCase) -> None:
        result = test_case.interval.length
        assert_array_equal(result, test_case.expected)


class TestZero(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: type
        interval: Interval

        @property
        def label(self) -> str:
            left_type = type(self.interval.left).__name__
            right_type = type(self.interval.right).__name__
            return f"{left_type}__{right_type}"

    test_cases = [
        TestCase(interval=Interval(True, True), expected=int),
        TestCase(interval=Interval(1, 2), expected=int),
        TestCase(interval=Interval(1.0, 2.0), expected=float),
        TestCase(interval=Interval(np.int8(1), np.int8(2)), expected=np.int8),
        TestCase(interval=Interval(np.int32(1), np.int32(2)), expected=np.int32),
        TestCase(interval=Interval(np.int64(1), np.int64(2)), expected=np.int64),
        TestCase(
            interval=Interval(np.float32(1.0), np.float32(2.0)),
            expected=np.float32,
        ),
        TestCase(
            interval=Interval(np.float64(1.0), np.float64(2.0)),
            expected=np.float64,
        ),
        TestCase(interval=Interval(True, 1), expected=int),
        TestCase(interval=Interval(1, True), expected=int),
        TestCase(interval=Interval(True, 1.0), expected=float),
        TestCase(interval=Interval(1.0, True), expected=float),
        TestCase(interval=Interval(1, 1.0), expected=float),
        TestCase(interval=Interval(1.0, 1), expected=float),
        TestCase(interval=Interval(np.int8(1), np.int32(2)), expected=np.int32),
        TestCase(interval=Interval(np.int32(1), np.int8(2)), expected=np.int32),
        TestCase(interval=Interval(np.int8(1), np.int64(2)), expected=np.int64),
        TestCase(interval=Interval(np.int64(1), np.int8(2)), expected=np.int64),
        TestCase(interval=Interval(np.int32(1), np.int64(2)), expected=np.int64),
        TestCase(interval=Interval(np.int64(1), np.int32(2)), expected=np.int64),
        TestCase(
            interval=Interval(np.float32(1.0), np.float64(2.0)),
            expected=np.float64,
        ),
        TestCase(
            interval=Interval(np.float64(1.0), np.float32(2.0)),
            expected=np.float64,
        ),
        TestCase(interval=Interval(1, np.int8(2)), expected=np.int8),
        TestCase(interval=Interval(np.int8(1), 257), expected=np.int8),
        TestCase(interval=Interval(1, np.int32(2)), expected=np.int32),
        TestCase(interval=Interval(np.int32(1), 2), expected=np.int32),
        TestCase(interval=Interval(1.0, np.float32(2.0)), expected=np.float32),
        TestCase(interval=Interval(np.float32(1.0), 2.0), expected=np.float32),
        TestCase(interval=Interval(1.0, np.float64(2.0)), expected=np.float64),
        TestCase(interval=Interval(np.float64(1.0), 2.0), expected=np.float64),
        TestCase(interval=Interval(1, np.float32(2.0)), expected=np.float32),
        TestCase(interval=Interval(np.float32(1.0), 2), expected=np.float32),
        TestCase(interval=Interval(1, np.float64(2.0)), expected=np.float64),
        TestCase(interval=Interval(np.float64(1.0), 2), expected=np.float64),
        TestCase(interval=Interval(np.int8(1), np.float32(2.0)), expected=np.float32),
        TestCase(interval=Interval(np.float32(1.0), np.int8(2)), expected=np.float32),
        TestCase(interval=Interval(np.int32(1), np.float32(2.0)), expected=np.float64),
        TestCase(interval=Interval(np.float32(1.0), np.int32(2)), expected=np.float64),
        TestCase(interval=Interval(np.int64(1), np.float32(2.0)), expected=np.float64),
        TestCase(interval=Interval(np.float32(1.0), np.int64(2)), expected=np.float64),
        TestCase(interval=Interval(np.int8(1), np.float64(2.0)), expected=np.float64),
        TestCase(interval=Interval(np.float64(1.0), np.int8(2)), expected=np.float64),
        TestCase(interval=Interval(np.int32(1), np.float64(2.0)), expected=np.float64),
        TestCase(interval=Interval(np.float64(1.0), np.int32(2)), expected=np.float64),
        TestCase(interval=Interval(np.int64(1), np.float64(2.0)), expected=np.float64),
        TestCase(interval=Interval(np.float64(1.0), np.int64(2)), expected=np.float64),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_zero_type(self, test_case: TestCase) -> None:
        result = test_case.interval.zero
        assert type(result) == test_case.expected
        assert_array_equal(result, test_case.expected(0))


class TestMidpoint(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Optional[Float]
        interval: Interval

        @property
        def label(self) -> str:
            return f"[{self.interval.left},{self.interval.right}]"

    test_cases = [
        TestCase(interval=Interval(0.0, 2.0), expected=1.0),
        TestCase(interval=Interval(1.0, 5.0), expected=3.0),
        TestCase(interval=Interval(-10.0, 10.0), expected=0.0),
        TestCase(interval=Interval(2.5, 7.5), expected=5.0),
        TestCase(
            interval=Interval(np.float32(0.0), np.float32(4.0)),
            expected=np.float32(2.0),
        ),
        TestCase(
            interval=Interval(np.float64(10.0), np.float64(20.0)),
            expected=np.float64(15.0),
        ),
        TestCase(interval=Interval(-np.inf, 0.0), expected=-np.inf),
        TestCase(interval=Interval(0.0, np.inf), expected=np.inf),
        TestCase(interval=Interval(-np.inf, np.inf), expected=np.nan),
        TestCase(interval=Interval(1.0, 1.0), expected=None),
        TestCase(interval=Interval(5.0, 3.0), expected=None),
        TestCase(interval=Interval(np.float32(10.0), np.float32(5.0)), expected=None),
        TestCase(interval=Interval(np.inf, np.inf), expected=None),
        TestCase(interval=Interval(np.nan, 1.0), expected=None),
        TestCase(interval=Interval(0.0, np.nan), expected=None),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_midpoint(self, test_case: TestCase) -> None:
        result = test_case.interval.midpoint
        if test_case.expected is None:
            assert result is None
        else:
            assert_array_equal(result, test_case.expected)


class TestIntersection(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Union[Interval, Type[Exception]]
        interval1: Interval
        interval2: Union[Interval, str]
        match: Optional[str] = None

        @property
        def label(self) -> str:
            error_suffix = "_error" if isinstance(self.expected, type) and issubclass(self.expected, Exception) else ""
            interval2_str = (
                f"[{self.interval2.left},{self.interval2.right}]"
                if isinstance(self.interval2, Interval)
                else str(self.interval2)
            )
            return f"[{self.interval1.left},{self.interval1.right}]_{interval2_str}{error_suffix}"

    test_cases = [
        TestCase(
            interval1=Interval(1.0, 5.0),
            interval2=Interval(3.0, 7.0),
            expected=Interval(3.0, 5.0),
        ),
        TestCase(
            interval1=Interval(0.0, 10.0),
            interval2=Interval(2.0, 8.0),
            expected=Interval(2.0, 8.0),
        ),
        TestCase(
            interval1=Interval(5.0, 10.0),
            interval2=Interval(1.0, 6.0),
            expected=Interval(5.0, 6.0),
        ),
        TestCase(
            interval1=Interval(1.0, 3.0),
            interval2=Interval(5.0, 7.0),
            expected=Interval(5.0, 3.0),
        ),
        TestCase(
            interval1=Interval(1.0, 5.0),
            interval2=Interval(5.0, 10.0),
            expected=Interval(5.0, 5.0),
        ),
        TestCase(
            interval1=Interval(np.float32(2.0), np.float32(6.0)),
            interval2=Interval(np.float32(4.0), np.float32(8.0)),
            expected=Interval(4.0, 6.0),
        ),
        TestCase(
            interval1=Interval(5.0, 3.0),
            interval2=Interval(1.0, 10.0),
            expected=Interval(5.0, 3.0),
        ),
        TestCase(
            interval1=Interval(1.0, 10.0),
            interval2=Interval(5.0, 3.0),
            expected=Interval(5.0, 3.0),
        ),
        TestCase(
            interval1=Interval(5.0, 3.0),
            interval2=Interval(8.0, 6.0),
            expected=Interval(8.0, 3.0),
        ),
        TestCase(
            interval1=Interval(-np.inf, 5.0),
            interval2=Interval(0.0, np.inf),
            expected=Interval(0.0, 5.0),
        ),
        TestCase(
            interval1=Interval(-np.inf, np.inf),
            interval2=Interval(0.0, 10.0),
            expected=Interval(0.0, 10.0),
        ),
        TestCase(
            interval1=Interval(0.0, np.inf),
            interval2=Interval(5.0, np.inf),
            expected=Interval(5.0, np.inf),
        ),
        TestCase(
            interval1=Interval(1.0, 5.0),
            interval2="not_interval",
            expected=TypeError,
            match="Expected Interval",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_intersection(self, test_case: TestCase) -> None:
        other = test_case.interval2 if isinstance(test_case.interval2, Interval) else test_case.interval2

        if not expect_error(
            test_case.interval1.intersection,
            test_case.expected,
            other,
            match=test_case.match,
        ):
            assert isinstance(other, Interval)
            result = test_case.interval1.intersection(other)
            assert result == test_case.expected


class TestContains(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: bool
        interval1: Interval
        interval2: Interval

        @property
        def label(self) -> str:
            return f"[{self.interval1.left},{self.interval1.right}]_contains_[{self.interval2.left},{self.interval2.right}]_{self.expected}"

    test_cases = [
        TestCase(
            interval1=Interval(0.0, 10.0),
            interval2=Interval(2.0, 8.0),
            expected=True,
        ),
        TestCase(
            interval1=Interval(1.0, 5.0),
            interval2=Interval(1.0, 5.0),
            expected=True,
        ),
        TestCase(
            interval1=Interval(0.0, 10.0),
            interval2=Interval(0.0, 10.0),
            expected=True,
        ),
        TestCase(
            interval1=Interval(np.float32(5.0), np.float32(15.0)),
            interval2=Interval(np.float32(7.0), np.float32(12.0)),
            expected=True,
        ),
        TestCase(
            interval1=Interval(-np.inf, np.inf),
            interval2=Interval(0.0, 10.0),
            expected=True,
        ),
        TestCase(
            interval1=Interval(-np.inf, 5.0),
            interval2=Interval(-10.0, 3.0),
            expected=True,
        ),
        TestCase(
            interval1=Interval(0.0, np.inf),
            interval2=Interval(5.0, 100.0),
            expected=True,
        ),
        TestCase(
            interval1=Interval(1.0, 5.0),
            interval2=Interval(3.0, 7.0),
            expected=False,
        ),
        TestCase(
            interval1=Interval(1.0, 5.0),
            interval2=Interval(0.0, 10.0),
            expected=False,
        ),
        TestCase(
            interval1=Interval(5.0, 10.0),
            interval2=Interval(1.0, 6.0),
            expected=False,
        ),
        TestCase(
            interval1=Interval(np.float64(3.0), np.float64(8.0)),
            interval2=Interval(np.float64(1.0), np.float64(4.0)),
            expected=False,
        ),
        TestCase(
            interval1=Interval(0.0, 10.0),
            interval2=Interval(-np.inf, 5.0),
            expected=False,
        ),
        TestCase(
            interval1=Interval(5.0, 3.0),
            interval2=Interval(1.0, 10.0),
            expected=False,
        ),
        TestCase(
            interval1=Interval(1.0, 10.0),
            interval2=Interval(5.0, 3.0),
            expected=True,
        ),
        TestCase(
            interval1=Interval(5.0, 3.0),
            interval2=Interval(8.0, 6.0),
            expected=True,
        ),
        TestCase(
            interval1=Interval(np.float32(7.0), np.float32(7.0)),
            interval2=Interval(np.float32(3.0), np.float32(5.0)),
            expected=False,
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_contains(self, test_case: TestCase) -> None:
        assert test_case.interval1.contains(test_case.interval2) == test_case.expected


class TestFloat(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Interval

        @property
        def label(self) -> str:
            return f"left_{type(self.expected.left).__name__}_right_{type(self.expected.right).__name__}"

    test_cases = [
        TestCase(expected=Interval(np.float32(1.5), np.float32(3.5))),
        TestCase(expected=Interval(np.float64(2.0), np.float64(8.0))),
        TestCase(expected=Interval(np.float32(-5.0), np.float32(5.0))),
        TestCase(expected=Interval(1.0, 5.0)),
        TestCase(expected=Interval(np.float64(10.5), np.float64(20.5))),
        TestCase(expected=Interval(-np.inf, np.inf)),
        TestCase(expected=Interval(np.float32(-np.inf), np.float32(5.0))),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_float(self, test_case: TestCase) -> None:
        result = test_case.expected.float()
        assert isinstance(result.left, float)
        assert isinstance(result.right, float)
        assert_array_equal(result.left, float(test_case.expected.left))
        assert_array_equal(result.right, float(test_case.expected.right))


class TestUnit:
    def test_unit_returns_zero_to_one(self) -> None:
        result = Interval.unit()
        assert result.left == 0.0
        assert result.right == 1.0
        assert isinstance(result.left, float)
        assert isinstance(result.right, float)

    def test_unit_is_valid(self) -> None:
        result = Interval.unit()
        assert bool(result) is True


class TestFromEdges(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Union[int, Type[Exception]]
        edges: Union[np.ndarray, List[float]]
        match: Optional[str] = None

        @property
        def label(self) -> str:
            error_suffix = "_error" if isinstance(self.expected, type) and issubclass(self.expected, Exception) else ""
            dtype_name = self.edges.dtype.name if isinstance(self.edges, np.ndarray) else type(self.edges).__name__
            return f"dtype_{dtype_name}_len_{len(self.edges)}{error_suffix}"

    test_cases = [
        TestCase(edges=np.array([0.0, 1.0, 2.0], dtype=np.float32), expected=2),
        TestCase(edges=np.array([0.0, 2.0, 5.0, 10.0], dtype=np.float64), expected=3),
        TestCase(
            edges=np.array([1.0, 3.0, 7.0, 15.0, 31.0], dtype=np.float32),
            expected=4,
        ),
        TestCase(edges=np.array([-10.0, 0.0, 10.0], dtype=np.float64), expected=2),
        TestCase(edges=np.array([0.0, 1.0], dtype=np.float32), expected=1),
        TestCase(
            edges=[0.0, 1.0, 2.0],
            expected=TypeError,
            match="edges must be an Array",
        ),
        TestCase(
            edges=np.array([1.0], dtype=np.float32),
            expected=ValueError,
            match="At least two edges",
        ),
        TestCase(
            edges=np.array([], dtype=np.float64),
            expected=ValueError,
            match="At least two edges",
        ),
        TestCase(
            edges=np.array([3.0, 2.0, 1.0], dtype=np.float32),
            expected=ValueError,
            match="strictly increasing",
        ),
        TestCase(
            edges=np.array([1.0, 2.0, 2.0, 3.0], dtype=np.float64),
            expected=ValueError,
            match="strictly increasing",
        ),
        TestCase(
            edges=np.array([1.0, 3.0, 2.0], dtype=np.float32),
            expected=ValueError,
            match="strictly increasing",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_from_edges(self, test_case: TestCase) -> None:
        if not expect_error(
            Interval.from_edges,
            test_case.expected,
            test_case.edges,
            match=test_case.match,
        ):
            result = Interval.from_edges(test_case.edges)
            assert len(result) == test_case.expected
            assert all(isinstance(interval, Interval) for interval in result)

            for i, interval in enumerate(result):
                assert_array_equal(interval.left, test_case.edges[i])
                assert_array_equal(interval.right, test_case.edges[i + 1])
                assert bool(interval) is True


class TestEdgeCases:
    def test_zero_length_interval_operations(self) -> None:
        interval = Interval(5.0, 5.0)
        assert bool(interval) is False
        assert_array_equal(interval.length, 0.0)
        assert interval.midpoint is None

    def test_negative_length_interval_operations(self) -> None:
        interval = Interval(10.0, 5.0)
        assert bool(interval) is False
        assert_array_equal(interval.length, 0.0)
        assert interval.midpoint is None

    def test_intersection_of_invalid_intervals(self) -> None:
        invalid1 = Interval(5.0, 3.0)
        invalid2 = Interval(8.0, 6.0)
        result = invalid1.intersection(invalid2)
        assert result == Interval(8.0, 3.0)
        assert bool(result) is False

    def test_contains_with_both_invalid(self) -> None:
        invalid1 = Interval(5.0, 3.0)
        invalid2 = Interval(8.0, 6.0)
        assert invalid1.contains(invalid2) is True

    def test_contains_valid_in_invalid(self) -> None:
        invalid = Interval(5.0, 3.0)
        valid = Interval(1.0, 10.0)
        assert invalid.contains(valid) is False

    def test_contains_invalid_in_valid(self) -> None:
        valid = Interval(1.0, 10.0)
        invalid = Interval(5.0, 3.0)
        assert valid.contains(invalid) is True

    def test_float_preserves_invalid_interval(self) -> None:
        invalid = Interval(np.float32(10.0), np.float32(5.0))
        result = invalid.float()
        assert isinstance(result.left, float)
        assert isinstance(result.right, float)
        assert_array_equal(result.left, 10.0)
        assert_array_equal(result.right, 5.0)
        assert bool(result) is False

    def test_unbounded_interval_with_negative_infinity(self) -> None:
        interval = Interval(-np.inf, 5.0)
        assert bool(interval) is True
        assert_array_equal(interval.length, np.inf)
        assert_array_equal(interval.midpoint, -np.inf)

    def test_unbounded_interval_with_positive_infinity(self) -> None:
        interval = Interval(0.0, np.inf)
        assert bool(interval) is True
        assert_array_equal(interval.length, np.inf)
        assert_array_equal(interval.midpoint, np.inf)

    def test_unbounded_interval_both_infinities(self) -> None:
        interval = Interval(-np.inf, np.inf)
        assert bool(interval) is True
        assert_array_equal(interval.length, np.inf)
        assert_array_equal(interval.midpoint, np.nan)

    def test_intersection_with_unbounded_intervals(self) -> None:
        unbounded = Interval(-np.inf, np.inf)
        bounded = Interval(0.0, 10.0)
        result = unbounded.intersection(bounded)
        assert result == bounded

    def test_contains_with_unbounded_intervals(self) -> None:
        unbounded = Interval(-np.inf, np.inf)
        bounded = Interval(0.0, 10.0)
        assert unbounded.contains(bounded) is True
        assert bounded.contains(unbounded) is False

    def test_interval_with_nan_left(self) -> None:
        interval = Interval(np.nan, 5.0)
        assert bool(interval) is False
        assert interval.midpoint is None

    def test_interval_with_nan_right(self) -> None:
        interval = Interval(0.0, np.nan)
        assert bool(interval) is False
        assert interval.midpoint is None

    def test_interval_with_both_nan(self) -> None:
        interval = Interval(np.nan, np.nan)
        assert bool(interval) is False
        assert interval.midpoint is None

    def test_infinity_equality_intervals(self) -> None:
        interval1 = Interval(-np.inf, 0.0)
        interval2 = Interval(-np.inf, 0.0)
        assert interval1 == interval2

    def test_infinity_inequality_intervals(self) -> None:
        interval1 = Interval(-np.inf, 0.0)
        interval2 = Interval(0.0, np.inf)
        assert interval1 != interval2
