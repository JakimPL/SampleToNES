from dataclasses import dataclass
from typing import List, Optional, Type, Union

import numpy as np
import pytest

from sampletones.structures.histogram.interval import Interval
from sampletones.types.array import Float
from tests.sampletones.errors import expect_error


class TestBool:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        left: Float
        right: Float
        expected: bool

        @property
        def test_id(self) -> str:
            return f"left_{self.left}_right_{self.right}_expect_{self.expected}"

    test_cases = [
        TestCase(left=0.0, right=1.0, expected=True),
        TestCase(left=1.0, right=5.0, expected=True),
        TestCase(left=-10.0, right=10.0, expected=True),
        TestCase(left=np.float32(0.0), right=np.float32(1.0), expected=True),
        TestCase(left=np.float64(5.5), right=np.float64(10.5), expected=True),
        TestCase(left=1.0, right=1.0, expected=False),
        TestCase(left=5.0, right=5.0, expected=False),
        TestCase(left=5.0, right=3.0, expected=False),
        TestCase(left=np.float32(2.0), right=np.float32(1.0), expected=False),
        TestCase(left=np.float64(10.0), right=np.float64(10.0), expected=False),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_bool(self, test_case: TestCase) -> None:
        interval = Interval(test_case.left, test_case.right)
        assert bool(interval) == test_case.expected


class TestLength:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        left: Float
        right: Float
        expected: Float

        @property
        def test_id(self) -> str:
            return f"left_{self.left}_right_{self.right}"

    test_cases = [
        TestCase(left=0.0, right=1.0, expected=1.0),
        TestCase(left=0.0, right=5.0, expected=5.0),
        TestCase(left=2.0, right=7.0, expected=5.0),
        TestCase(left=-5.0, right=5.0, expected=10.0),
        TestCase(left=np.float32(1.5), right=np.float32(3.5), expected=2.0),
        TestCase(left=np.float64(10.0), right=np.float64(15.0), expected=5.0),
        TestCase(left=1.0, right=1.0, expected=0.0),
        TestCase(left=5.0, right=3.0, expected=0.0),
        TestCase(left=np.float32(10.0), right=np.float32(5.0), expected=0.0),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_length(self, test_case: TestCase) -> None:
        interval = Interval(test_case.left, test_case.right)
        assert interval.length == pytest.approx(test_case.expected)


class TestMidpoint:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        left: Float
        right: Float
        expected: Optional[Float]

        @property
        def test_id(self) -> str:
            return f"left_{self.left}_right_{self.right}"

    test_cases = [
        TestCase(left=0.0, right=2.0, expected=1.0),
        TestCase(left=1.0, right=5.0, expected=3.0),
        TestCase(left=-10.0, right=10.0, expected=0.0),
        TestCase(left=2.5, right=7.5, expected=5.0),
        TestCase(left=np.float32(0.0), right=np.float32(4.0), expected=2.0),
        TestCase(left=np.float64(10.0), right=np.float64(20.0), expected=15.0),
        TestCase(left=1.0, right=1.0, expected=None),
        TestCase(left=5.0, right=3.0, expected=None),
        TestCase(left=np.float32(10.0), right=np.float32(5.0), expected=None),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_midpoint(self, test_case: TestCase) -> None:
        interval = Interval(test_case.left, test_case.right)
        if test_case.expected is None:
            assert interval.midpoint is None
        else:
            assert interval.midpoint == pytest.approx(test_case.expected)


class TestIntersection:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        left1: Float
        right1: Float
        left2: Float
        right2: Float
        expected_left: Float
        expected_right: Float
        expected: Union[Interval, Type[Exception]]
        match: Optional[str] = None

        @property
        def test_id(self) -> str:
            error_suffix = "_error" if isinstance(self.expected, type) and issubclass(self.expected, Exception) else ""
            return f"[{self.left1},{self.right1}]_[{self.left2},{self.right2}]{error_suffix}"

    test_cases = [
        TestCase(
            left1=1.0, right1=5.0, left2=3.0, right2=7.0, expected_left=3.0, expected_right=5.0, expected=Interval
        ),
        TestCase(
            left1=0.0, right1=10.0, left2=2.0, right2=8.0, expected_left=2.0, expected_right=8.0, expected=Interval
        ),
        TestCase(
            left1=5.0, right1=10.0, left2=1.0, right2=6.0, expected_left=5.0, expected_right=6.0, expected=Interval
        ),
        TestCase(
            left1=1.0, right1=3.0, left2=5.0, right2=7.0, expected_left=5.0, expected_right=3.0, expected=Interval
        ),
        TestCase(
            left1=1.0, right1=5.0, left2=5.0, right2=10.0, expected_left=5.0, expected_right=5.0, expected=Interval
        ),
        TestCase(
            left1=np.float32(2.0),
            right1=np.float32(6.0),
            left2=np.float32(4.0),
            right2=np.float32(8.0),
            expected_left=4.0,
            expected_right=6.0,
            expected=Interval,
        ),
        TestCase(
            left1=5.0, right1=3.0, left2=1.0, right2=10.0, expected_left=5.0, expected_right=3.0, expected=Interval
        ),
        TestCase(
            left1=1.0, right1=10.0, left2=5.0, right2=3.0, expected_left=5.0, expected_right=3.0, expected=Interval
        ),
        TestCase(
            left1=5.0, right1=3.0, left2=8.0, right2=6.0, expected_left=8.0, expected_right=3.0, expected=Interval
        ),
        TestCase(
            left1=1.0,
            right1=5.0,
            left2="not_interval",
            right2=0.0,
            expected_left=0.0,
            expected_right=0.0,
            expected=TypeError,
            match="Expected Interval",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_intersection(self, test_case: TestCase) -> None:
        interval1 = Interval(test_case.left1, test_case.right1)
        other = (
            test_case.left2
            if isinstance(test_case.expected, type) and issubclass(test_case.expected, Exception)
            else Interval(test_case.left2, test_case.right2)
        )

        if not expect_error(interval1.intersection, test_case.expected, other, match=test_case.match):
            result = interval1.intersection(other)
            assert result.left == pytest.approx(test_case.expected_left)
            assert result.right == pytest.approx(test_case.expected_right)


class TestContains:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        left1: Float
        right1: Float
        left2: Float
        right2: Float
        expected: bool

        @property
        def test_id(self) -> str:
            return f"[{self.left1},{self.right1}]_contains_[{self.left2},{self.right2}]_{self.expected}"

    test_cases = [
        TestCase(left1=0.0, right1=10.0, left2=2.0, right2=8.0, expected=True),
        TestCase(left1=1.0, right1=5.0, left2=1.0, right2=5.0, expected=True),
        TestCase(left1=0.0, right1=10.0, left2=0.0, right2=10.0, expected=True),
        TestCase(
            left1=np.float32(5.0),
            right1=np.float32(15.0),
            left2=np.float32(7.0),
            right2=np.float32(12.0),
            expected=True,
        ),
        TestCase(left1=1.0, right1=5.0, left2=3.0, right2=7.0, expected=False),
        TestCase(left1=1.0, right1=5.0, left2=0.0, right2=10.0, expected=False),
        TestCase(left1=5.0, right1=10.0, left2=1.0, right2=6.0, expected=False),
        TestCase(
            left1=np.float64(3.0), right1=np.float64(8.0), left2=np.float64(1.0), right2=np.float64(4.0), expected=False
        ),
        TestCase(left1=5.0, right1=3.0, left2=1.0, right2=10.0, expected=False),
        TestCase(left1=1.0, right1=10.0, left2=5.0, right2=3.0, expected=True),
        TestCase(left1=5.0, right1=3.0, left2=8.0, right2=6.0, expected=True),
        TestCase(
            left1=np.float32(7.0), right1=np.float32(7.0), left2=np.float32(3.0), right2=np.float32(5.0), expected=False
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_contains(self, test_case: TestCase) -> None:
        interval1 = Interval(test_case.left1, test_case.right1)
        interval2 = Interval(test_case.left2, test_case.right2)
        assert interval1.contains(interval2) == test_case.expected


class TestRelativeMeasure:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        left1: Float
        right1: Float
        left2: Float
        right2: Float
        expected: Union[Float, Type[Exception]]
        match: Optional[str] = None

        @property
        def test_id(self) -> str:
            error_suffix = "_error" if isinstance(self.expected, type) and issubclass(self.expected, Exception) else ""
            return f"[{self.left1},{self.right1}]_measure_[{self.left2},{self.right2}]{error_suffix}"

    test_cases = [
        TestCase(left1=0.0, right1=10.0, left2=0.0, right2=10.0, expected=1.0),
        TestCase(left1=0.0, right1=10.0, left2=0.0, right2=5.0, expected=0.5),
        TestCase(left1=0.0, right1=10.0, left2=5.0, right2=10.0, expected=0.5),
        TestCase(left1=3.0, right1=7.0, left2=4.0, right2=6.0, expected=0.5),
        TestCase(left1=3.0, right1=7.0, left2=6.0, right2=15.0, expected=0.25),
        TestCase(left1=0.0, right1=10.0, left2=15.0, right2=20.0, expected=0.0),
        TestCase(
            left1=np.float32(2.0),
            right1=np.float32(8.0),
            left2=np.float32(3.0),
            right2=np.float32(5.0),
            expected=pytest.approx(2.0 / 6.0),
        ),
        TestCase(
            left1=np.float64(0.0),
            right1=np.float64(100.0),
            left2=np.float64(25.0),
            right2=np.float64(75.0),
            expected=0.5,
        ),
        TestCase(left1=5.0, right1=3.0, left2=1.0, right2=10.0, expected=0.0),
        TestCase(left1=1.0, right1=10.0, left2=5.0, right2=3.0, expected=0.0),
        TestCase(left1=5.0, right1=3.0, left2=8.0, right2=6.0, expected=0.0),
        TestCase(
            left1=1.0, right1=5.0, left2="not_interval", right2=0.0, expected=TypeError, match="Expected Interval"
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_relative_measure(self, test_case: TestCase) -> None:
        interval1 = Interval(test_case.left1, test_case.right1)
        other = (
            test_case.left2
            if isinstance(test_case.expected, type) and issubclass(test_case.expected, Exception)
            else Interval(test_case.left2, test_case.right2)
        )

        if not expect_error(interval1.relative_measure, test_case.expected, other, match=test_case.match):
            result = interval1.relative_measure(other)
            if isinstance(test_case.expected, float):
                assert result == pytest.approx(test_case.expected)
            else:
                assert result == test_case.expected


class TestFloat:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        left: Float
        right: Float

        @property
        def test_id(self) -> str:
            return f"left_{type(self.left).__name__}_right_{type(self.right).__name__}"

    test_cases = [
        TestCase(left=np.float32(1.5), right=np.float32(3.5)),
        TestCase(left=np.float64(2.0), right=np.float64(8.0)),
        TestCase(left=np.float32(-5.0), right=np.float32(5.0)),
        TestCase(left=1.0, right=5.0),
        TestCase(left=np.float64(10.5), right=np.float64(20.5)),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_float(self, test_case: TestCase) -> None:
        interval = Interval(test_case.left, test_case.right)
        result = interval.float()
        assert isinstance(result.left, float)
        assert isinstance(result.right, float)
        assert result.left == pytest.approx(float(test_case.left))
        assert result.right == pytest.approx(float(test_case.right))


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


class TestFromEdges:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        edges: Union[np.ndarray, List[float]]
        expected: Union[int, Type[Exception]]
        match: Optional[str] = None

        @property
        def test_id(self) -> str:
            error_suffix = "_error" if isinstance(self.expected, type) and issubclass(self.expected, Exception) else ""
            dtype_name = self.edges.dtype.name if hasattr(self.edges, "dtype") else type(self.edges).__name__
            return f"dtype_{dtype_name}_len_{len(self.edges)}{error_suffix}"

    test_cases = [
        TestCase(edges=np.array([0.0, 1.0, 2.0], dtype=np.float32), expected=2),
        TestCase(edges=np.array([0.0, 2.0, 5.0, 10.0], dtype=np.float64), expected=3),
        TestCase(edges=np.array([1.0, 3.0, 7.0, 15.0, 31.0], dtype=np.float32), expected=4),
        TestCase(edges=np.array([-10.0, 0.0, 10.0], dtype=np.float64), expected=2),
        TestCase(edges=np.array([0.0, 1.0], dtype=np.float32), expected=1),
        TestCase(edges=[0.0, 1.0, 2.0], expected=TypeError, match="edges must be an Array"),
        TestCase(edges=np.array([1.0], dtype=np.float32), expected=ValueError, match="At least two edges"),
        TestCase(edges=np.array([], dtype=np.float64), expected=ValueError, match="At least two edges"),
        TestCase(edges=np.array([3.0, 2.0, 1.0], dtype=np.float32), expected=ValueError, match="strictly increasing"),
        TestCase(
            edges=np.array([1.0, 2.0, 2.0, 3.0], dtype=np.float64), expected=ValueError, match="strictly increasing"
        ),
        TestCase(edges=np.array([1.0, 3.0, 2.0], dtype=np.float32), expected=ValueError, match="strictly increasing"),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.test_id for tc in test_cases])
    def test_from_edges(self, test_case: TestCase) -> None:
        if not expect_error(Interval.from_edges, test_case.expected, test_case.edges, match=test_case.match):
            result = Interval.from_edges(test_case.edges)
            assert len(result) == test_case.expected
            assert all(isinstance(interval, Interval) for interval in result)

            for i, interval in enumerate(result):
                assert interval.left == pytest.approx(test_case.edges[i])
                assert interval.right == pytest.approx(test_case.edges[i + 1])
                assert bool(interval) is True


class TestEdgeCases:
    def test_zero_length_interval_operations(self) -> None:
        interval = Interval(5.0, 5.0)
        assert bool(interval) is False
        assert interval.length == 0.0
        assert interval.midpoint is None

    def test_negative_length_interval_operations(self) -> None:
        interval = Interval(10.0, 5.0)
        assert bool(interval) is False
        assert interval.length == 0.0
        assert interval.midpoint is None

    def test_intersection_of_invalid_intervals(self) -> None:
        invalid1 = Interval(5.0, 3.0)
        invalid2 = Interval(8.0, 6.0)
        result = invalid1.intersection(invalid2)
        assert result.left == 8.0
        assert result.right == 3.0
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

    def test_relative_measure_of_two_invalid_intervals(self) -> None:
        invalid1 = Interval(5.0, 3.0)
        invalid2 = Interval(8.0, 6.0)
        result = invalid1.relative_measure(invalid2)
        assert result == 0.0

    def test_relative_measure_valid_with_invalid_other(self) -> None:
        valid = Interval(1.0, 10.0)
        invalid = Interval(5.0, 3.0)
        result = valid.relative_measure(invalid)
        assert result == 0.0

    def test_float_preserves_invalid_interval(self) -> None:
        invalid = Interval(np.float32(10.0), np.float32(5.0))
        result = invalid.float()
        assert isinstance(result.left, float)
        assert isinstance(result.right, float)
        assert result.left == 10.0
        assert result.right == 5.0
        assert bool(result) is False
