from dataclasses import dataclass
from fractions import Fraction
from math import ceil, floor
from typing import Final, Tuple

import pytest

from sampletones_core.timing.distribution import nearest, split_by_halving
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase
from tests.suite.groove import is_proportional, surplus_rows

COMMON_BEAT: Final[int] = 4
BEATS_IN_A_LONG_BAR: Final[int] = 8


class TestNearest(BaseTestSuite):
    @pytest.mark.parametrize(
        ("value", "expected"),
        (
            (Fraction(7, 2), 4),
            (Fraction(36, 5), 7),
            (Fraction(38, 5), 8),
            (Fraction(-1, 2), 0),
            (Fraction(6), 6),
        ),
    )
    def test_a_half_rounds_up(self, value: Fraction, expected: int) -> None:
        assert nearest(value) == expected


class TestSplitByHalving(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Tuple[int, ...]
        total: int
        spans: Tuple[int, ...]
        row_ticks: Fraction

        @property
        def label(self) -> str:
            spans = "_".join(str(span) for span in self.spans)
            return f"total_{self.total}_over_{spans}"

    test_cases = (
        TestCase(
            total=115,
            spans=(4, 4, 4, 4),
            row_ticks=Fraction(36, 5),
            expected=(8, 7, 7, 7, 8, 7, 7, 7, 8, 7, 7, 7, 7, 7, 7, 7),
        ),
        TestCase(
            total=69,
            spans=(4, 4, 4, 4),
            row_ticks=Fraction(30, 7),
            expected=(5, 4, 5, 4, 5, 4, 4, 4, 5, 4, 4, 4, 5, 4, 4, 4),
        ),
        TestCase(
            total=24,
            spans=(4,),
            row_ticks=Fraction(6),
            expected=(6, 6, 6, 6),
        ),
        TestCase(
            total=29,
            spans=(4,),
            row_ticks=Fraction(29, 4),
            expected=(8, 7, 7, 7),
        ),
        TestCase(
            total=30,
            spans=(4,),
            row_ticks=Fraction(30, 4),
            expected=(8, 7, 8, 7),
        ),
        TestCase(
            total=31,
            spans=(4,),
            row_ticks=Fraction(31, 4),
            expected=(8, 8, 8, 7),
        ),
        TestCase(
            total=22,
            spans=(3,),
            row_ticks=Fraction(22, 3),
            expected=(8, 7, 7),
        ),
        TestCase(
            total=23,
            spans=(3,),
            row_ticks=Fraction(23, 3),
            expected=(8, 7, 8),
        ),
        TestCase(
            total=100,
            spans=(1,),
            row_ticks=Fraction(100),
            expected=(100,),
        ),
        TestCase(
            total=50,
            spans=(3, 3, 1),
            row_ticks=Fraction(36, 5),
            expected=(8, 7, 7, 7, 7, 7, 7),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_ticks_match(self, test_case: TestCase) -> None:
        ticks = split_by_halving(test_case.total, test_case.spans, row_ticks=test_case.row_ticks)

        assert ticks == test_case.expected
        assert sum(ticks) == test_case.total

    @pytest.mark.parametrize(
        ("rows", "strongest"),
        (
            (2, (0, 1)),
            (3, (0, 2, 1)),
            (4, (0, 2, 1, 3)),
            (6, (0, 3, 2, 5, 1, 4)),
            (8, (0, 4, 2, 6, 1, 5, 3, 7)),
        ),
    )
    def test_a_beat_gives_its_surplus_to_its_strongest_rows(self, rows: int, strongest: Tuple[int, ...]) -> None:
        """The first row takes the first surplus tick, the middle row the next, the quarters after them."""
        for surplus in range(1, rows):
            row_ticks = 7 + Fraction(surplus, rows)
            ticks = split_by_halving(7 * rows + surplus, (rows,), row_ticks=row_ticks)

            assert surplus_rows(ticks, row_ticks) == tuple(sorted(strongest[:surplus]))

    @pytest.mark.parametrize("surplus", range(1, BEATS_IN_A_LONG_BAR))
    def test_a_bar_gives_its_surplus_to_its_strongest_beats(self, surplus: int) -> None:
        """Eight beats share their surplus ticks as the first half of them, then the halves of those."""
        strongest = (0, 4, 2, 6, 1, 5, 3, 7)
        rows = COMMON_BEAT * BEATS_IN_A_LONG_BAR
        row_ticks = 7 + Fraction(surplus, rows)
        ticks = split_by_halving(
            7 * rows + surplus,
            (COMMON_BEAT,) * BEATS_IN_A_LONG_BAR,
            row_ticks=row_ticks,
        )
        longer_beats = tuple(
            beat
            for beat in range(BEATS_IN_A_LONG_BAR)
            if sum(ticks[beat * COMMON_BEAT : (beat + 1) * COMMON_BEAT]) > 7 * COMMON_BEAT
        )

        assert longer_beats == tuple(sorted(strongest[:surplus]))

    @pytest.mark.parametrize("spans", ((4, 4, 4, 4), (3, 3, 1), (5, 5, 5), (2,), (7,), (6, 6, 4), (1, 1, 1)))
    @pytest.mark.parametrize("row_ticks", (Fraction(36, 5), Fraction(30, 7), Fraction(11, 4), Fraction(13, 10)))
    def test_every_total_the_rows_carry_keeps_each_row_proportional(
        self,
        spans: Tuple[int, ...],
        row_ticks: Fraction,
    ) -> None:
        rows = sum(spans)
        for total in range(rows * floor(row_ticks), rows * ceil(row_ticks) + 1):
            ticks = split_by_halving(total, spans, row_ticks=row_ticks)

            assert sum(ticks) == total
            assert len(ticks) == rows
            assert is_proportional(ticks, row_ticks)

    def test_no_span_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="At least one span"):
            split_by_halving(10, (), row_ticks=Fraction(5))

    def test_an_empty_span_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least 1 row"):
            split_by_halving(10, (4, 0), row_ticks=Fraction(5, 2))

    @pytest.mark.parametrize("total", (27, 33))
    def test_a_total_the_rows_cannot_carry_is_rejected(self, total: int) -> None:
        with pytest.raises(ValueError, match="carry no total"):
            split_by_halving(total, (4,), row_ticks=Fraction(29, 4))
