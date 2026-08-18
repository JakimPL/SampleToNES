from dataclasses import dataclass
from typing import Tuple

import pytest

from sampletones_core.timing.distribution import distribute_by_halving, distribute_proportionally
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase


class TestDistributeProportionally(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Tuple[int, ...]
        total: int
        lengths: Tuple[int, ...]

        @property
        def label(self) -> str:
            spans = "_".join(str(length) for length in self.lengths)
            return f"total_{self.total}_over_{spans}"

    test_cases = (
        TestCase(
            total=69,
            lengths=(4, 4, 4, 4),
            expected=(18, 17, 17, 17),
        ),
        TestCase(
            total=69,
            lengths=(8, 8),
            expected=(35, 34),
        ),
        TestCase(
            total=274,
            lengths=(16, 16, 16, 16),
            expected=(69, 68, 69, 68),
        ),
        TestCase(
            total=17,
            lengths=(2, 2),
            expected=(9, 8),
        ),
        TestCase(
            total=18,
            lengths=(2, 2),
            expected=(9, 9),
        ),
        TestCase(
            total=100,
            lengths=(1,),
            expected=(100,),
        ),
        TestCase(
            total=0,
            lengths=(4, 4),
            expected=(0, 0),
        ),
        TestCase(
            total=69,
            lengths=(12, 4),
            expected=(52, 17),
        ),
        TestCase(
            total=10,
            lengths=(1, 1, 1),
            expected=(4, 3, 3),
        ),
        TestCase(
            total=11,
            lengths=(1, 1, 1),
            expected=(4, 4, 3),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_shares_match(self, test_case: TestCase) -> None:
        shares = distribute_proportionally(test_case.total, test_case.lengths)
        assert shares == test_case.expected
        assert sum(shares) == test_case.total

    def test_no_span_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="At least one span"):
            distribute_proportionally(10, ())

    def test_empty_span_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least 1 row"):
            distribute_proportionally(10, (4, 0))


class TestDistributeByHalving(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Tuple[int, ...]
        total: int
        rows: int

        @property
        def label(self) -> str:
            return f"total_{self.total}_over_{self.rows}_rows"

    test_cases = (
        TestCase(
            total=22,
            rows=4,
            expected=(6, 5, 6, 5),
        ),
        TestCase(
            total=69,
            rows=16,
            expected=(5, 4, 5, 4, 5, 4, 4, 4, 5, 4, 4, 4, 5, 4, 4, 4),
        ),
        TestCase(
            total=18,
            rows=4,
            expected=(5, 4, 5, 4),
        ),
        TestCase(
            total=17,
            rows=4,
            expected=(5, 4, 4, 4),
        ),
        TestCase(
            total=9,
            rows=2,
            expected=(5, 4),
        ),
        TestCase(
            total=100,
            rows=1,
            expected=(100,),
        ),
        TestCase(
            total=0,
            rows=5,
            expected=(0, 0, 0, 0, 0),
        ),
        TestCase(
            total=13,
            rows=3,
            expected=(5, 4, 4),
        ),
        TestCase(
            total=22,
            rows=5,
            expected=(5, 5, 4, 4, 4),
        ),
        TestCase(
            total=30,
            rows=7,
            expected=(5, 4, 5, 4, 4, 4, 4),
        ),
        TestCase(
            total=52,
            rows=12,
            expected=(5, 4, 4, 5, 4, 4, 5, 4, 4, 5, 4, 4),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_ticks_match(self, test_case: TestCase) -> None:
        ticks = distribute_by_halving(test_case.total, test_case.rows)
        assert ticks == test_case.expected
        assert sum(ticks) == test_case.total

    def test_absent_rows_are_rejected(self) -> None:
        with pytest.raises(ValueError, match="rows must be at least 1"):
            distribute_by_halving(10, 0)

    @pytest.mark.parametrize("rows", (1, 2, 3, 4, 5, 7, 8, 12, 16, 31, 64))
    def test_earlier_rows_run_at_least_as_long(self, rows: int) -> None:
        ticks = distribute_by_halving(rows * 4 + 1, rows)
        assert ticks[0] == max(ticks)
