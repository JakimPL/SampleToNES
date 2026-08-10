from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Final, Tuple

import pytest

from sampletones_core.timing.groove import Groove, calculate_groove
from sampletones_core.timing.metre import Metre
from sampletones_core.timing.rate import RowRate
from sampletones_shared.constants.project import REFERENCE_NES_FREQUENCY, REFERENCE_TEMPO
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase

MINIMUM_TICKS: Final[int] = 1
MAXIMUM_TICKS: Final[int] = 255

COMMON_TIME_BEAT: Final[int] = 4
COMMON_TIME_BAR: Final[int] = 16

REFERENCE_SPEED: Final[int] = 6


class TestGroove(BaseTestSuite):
    """One case table, read both for the ticks it produces and for the rules they obey."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Tuple[int, ...]
        tempo: int
        speed: int
        nes_frequency: int
        rows: int
        first_highlight: int
        second_highlight: int

        @property
        def label(self) -> str:
            return (
                f"tempo_{self.tempo}_speed_{self.speed}_{self.nes_frequency}hz"
                f"_{self.rows}r_{self.first_highlight}_{self.second_highlight}"
            )

        @property
        def metre(self) -> Metre:
            return Metre(
                rows=self.rows,
                first_highlight=self.first_highlight,
                second_highlight=self.second_highlight,
            )

        @property
        def groove(self) -> Groove:
            return calculate_groove(
                RowRate.from_parameters(
                    tempo=self.tempo,
                    speed=self.speed,
                    nes_frequency=self.nes_frequency,
                ),
                self.metre,
                minimum_ticks=MINIMUM_TICKS,
                maximum_ticks=MAXIMUM_TICKS,
            )

    test_cases = (
        TestCase(
            tempo=150,
            speed=6,
            nes_frequency=60,
            rows=16,
            first_highlight=4,
            second_highlight=16,
            expected=(6,) * 16,
        ),
        TestCase(
            tempo=150,
            speed=6,
            nes_frequency=30,
            rows=16,
            first_highlight=4,
            second_highlight=16,
            expected=(3,) * 16,
        ),
        TestCase(
            tempo=75,
            speed=6,
            nes_frequency=60,
            rows=16,
            first_highlight=4,
            second_highlight=16,
            expected=(12,) * 16,
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=60,
            rows=16,
            first_highlight=4,
            second_highlight=16,
            expected=(5, 4, 5, 4, 5, 4, 4, 4, 5, 4, 4, 4, 5, 4, 4, 4),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=15,
            rows=16,
            first_highlight=4,
            second_highlight=16,
            expected=(2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=24,
            rows=12,
            first_highlight=3,
            second_highlight=12,
            expected=(2, 2, 2, 2, 2, 1, 2, 2, 1, 2, 2, 1),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=25,
            rows=16,
            first_highlight=4,
            second_highlight=16,
            expected=(2, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=30,
            rows=16,
            first_highlight=4,
            second_highlight=16,
            expected=(3, 2, 2, 2, 2, 2, 2, 2, 3, 2, 2, 2, 2, 2, 2, 2),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=50,
            rows=16,
            first_highlight=4,
            second_highlight=16,
            expected=(4, 4, 4, 3, 4, 3, 4, 3, 4, 3, 4, 3, 4, 3, 4, 3),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=100,
            rows=16,
            first_highlight=4,
            second_highlight=16,
            expected=(8, 7, 7, 7, 7, 7, 7, 7, 8, 7, 7, 7, 7, 7, 7, 7),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=120,
            rows=8,
            first_highlight=4,
            second_highlight=16,
            expected=(9, 9, 9, 8, 9, 8, 9, 8),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=300,
            rows=8,
            first_highlight=4,
            second_highlight=16,
            expected=(22, 21, 22, 21, 22, 21, 21, 21),
        ),
        TestCase(
            tempo=37,
            speed=13,
            nes_frequency=25,
            rows=11,
            first_highlight=4,
            second_highlight=16,
            expected=(22,) * 11,
        ),
        TestCase(
            tempo=33,
            speed=7,
            nes_frequency=17,
            rows=13,
            first_highlight=3,
            second_highlight=12,
            expected=(9,) * 13,
        ),
        TestCase(
            tempo=137,
            speed=11,
            nes_frequency=23,
            rows=7,
            first_highlight=2,
            second_highlight=3,
            expected=(5, 5, 4, 5, 5, 4, 4),
        ),
        TestCase(
            tempo=251,
            speed=13,
            nes_frequency=199,
            rows=17,
            first_highlight=5,
            second_highlight=7,
            expected=(26, 26, 26, 26, 26, 26, 25, 26, 26, 26, 26, 25, 26, 25, 26, 26, 25),
        ),
        TestCase(
            tempo=97,
            speed=3,
            nes_frequency=41,
            rows=9,
            first_highlight=4,
            second_highlight=6,
            expected=(4, 3, 4, 3, 3, 3, 3, 3, 3),
        ),
        TestCase(
            tempo=128,
            speed=5,
            nes_frequency=96,
            rows=15,
            first_highlight=4,
            second_highlight=16,
            expected=(10, 9, 10, 9, 10, 9, 10, 9, 10, 9, 9, 9, 10, 9, 9),
        ),
        TestCase(
            tempo=100,
            speed=7,
            nes_frequency=45,
            rows=13,
            first_highlight=7,
            second_highlight=7,
            expected=(8, 8, 8, 8, 8, 8, 7, 8, 8, 8, 8, 8, 7),
        ),
        TestCase(
            tempo=43,
            speed=29,
            nes_frequency=31,
            rows=11,
            first_highlight=3,
            second_highlight=8,
            expected=(53, 53, 52, 53, 52, 52, 52, 52, 52, 52, 52),
        ),
        TestCase(
            tempo=199,
            speed=17,
            nes_frequency=47,
            rows=19,
            first_highlight=4,
            second_highlight=16,
            expected=(11, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=60,
            rows=1,
            first_highlight=4,
            second_highlight=16,
            expected=(4,),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=60,
            rows=2,
            first_highlight=4,
            second_highlight=16,
            expected=(5, 4),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=60,
            rows=3,
            first_highlight=4,
            second_highlight=16,
            expected=(5, 4, 4),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=60,
            rows=5,
            first_highlight=4,
            second_highlight=16,
            expected=(5, 4, 4, 4, 4),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=60,
            rows=7,
            first_highlight=4,
            second_highlight=16,
            expected=(5, 4, 5, 4, 4, 4, 4),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=60,
            rows=12,
            first_highlight=3,
            second_highlight=12,
            expected=(5, 4, 4, 5, 4, 4, 5, 4, 4, 4, 4, 4),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=60,
            rows=12,
            first_highlight=6,
            second_highlight=12,
            expected=(5, 4, 4, 5, 4, 4, 5, 4, 4, 4, 4, 4),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=60,
            rows=13,
            first_highlight=4,
            second_highlight=16,
            expected=(5, 4, 5, 4, 5, 4, 4, 4, 5, 4, 4, 4, 4),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=60,
            rows=17,
            first_highlight=4,
            second_highlight=16,
            expected=(5, 4, 5, 4, 5, 4, 4, 4, 5, 4, 4, 4, 5, 4, 4, 4, 4),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=60,
            rows=23,
            first_highlight=4,
            second_highlight=16,
            expected=(5, 4, 5, 4, 5, 4, 4, 4, 5, 4, 4, 4, 5, 4, 4, 4, 5, 4, 5, 4, 4, 4, 4),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=60,
            rows=32,
            first_highlight=4,
            second_highlight=16,
            expected=(5, 4, 5, 4, 5, 4, 4, 4, 5, 4, 4, 4, 5, 4, 4, 4, 5, 4, 4, 4, 5, 4, 4, 4, 5, 4, 4, 4, 5, 4, 4, 4),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=60,
            rows=60,
            first_highlight=4,
            second_highlight=16,
            expected=(
                5,
                4,
                5,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                5,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
            ),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=60,
            rows=64,
            first_highlight=4,
            second_highlight=16,
            expected=(
                5,
                4,
                5,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                5,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
                5,
                4,
                4,
                4,
            ),
        ),
        TestCase(
            tempo=105,
            speed=6,
            nes_frequency=60,
            rows=16,
            first_highlight=1,
            second_highlight=1,
            expected=(9, 9, 8, 9, 8, 9, 8, 9, 9, 8, 9, 8, 9, 8, 9, 8),
        ),
        TestCase(
            tempo=105,
            speed=6,
            nes_frequency=60,
            rows=16,
            first_highlight=2,
            second_highlight=4,
            expected=(9, 9, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8),
        ),
        TestCase(
            tempo=105,
            speed=6,
            nes_frequency=60,
            rows=16,
            first_highlight=3,
            second_highlight=4,
            expected=(9, 9, 9, 8, 9, 9, 8, 8, 9, 9, 8, 8, 9, 9, 8, 8),
        ),
        TestCase(
            tempo=105,
            speed=6,
            nes_frequency=60,
            rows=16,
            first_highlight=5,
            second_highlight=3,
            expected=(9, 9, 8, 9, 9, 8, 9, 9, 8, 9, 8, 8, 9, 9, 8, 8),
        ),
        TestCase(
            tempo=105,
            speed=6,
            nes_frequency=60,
            rows=16,
            first_highlight=16,
            second_highlight=4,
            expected=(9, 9, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8),
        ),
        TestCase(
            tempo=105,
            speed=6,
            nes_frequency=60,
            rows=16,
            first_highlight=64,
            second_highlight=64,
            expected=(9, 9, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8),
        ),
        TestCase(
            tempo=105,
            speed=6,
            nes_frequency=60,
            rows=12,
            first_highlight=4,
            second_highlight=6,
            expected=(9, 9, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8),
        ),
        TestCase(
            tempo=105,
            speed=6,
            nes_frequency=60,
            rows=20,
            first_highlight=4,
            second_highlight=8,
            expected=(9, 9, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8),
        ),
        TestCase(
            tempo=105,
            speed=6,
            nes_frequency=60,
            rows=9,
            first_highlight=2,
            second_highlight=6,
            expected=(9, 9, 9, 8, 9, 8, 9, 8, 8),
        ),
        TestCase(
            tempo=105,
            speed=6,
            nes_frequency=60,
            rows=15,
            first_highlight=5,
            second_highlight=15,
            expected=(9, 9, 8, 9, 8, 9, 9, 8, 9, 8, 9, 9, 8, 9, 8),
        ),
        TestCase(
            tempo=150,
            speed=1,
            nes_frequency=60,
            rows=16,
            first_highlight=4,
            second_highlight=16,
            expected=(1,) * 16,
        ),
        TestCase(
            tempo=151,
            speed=1,
            nes_frequency=60,
            rows=16,
            first_highlight=4,
            second_highlight=16,
            expected=(1,) * 16,
        ),
        TestCase(
            tempo=140,
            speed=1,
            nes_frequency=60,
            rows=16,
            first_highlight=4,
            second_highlight=16,
            expected=(2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1),
        ),
        TestCase(
            tempo=300,
            speed=1,
            nes_frequency=60,
            rows=16,
            first_highlight=4,
            second_highlight=16,
            expected=(1,) * 16,
        ),
        TestCase(
            tempo=255,
            speed=1,
            nes_frequency=60,
            rows=16,
            first_highlight=4,
            second_highlight=16,
            expected=(1,) * 16,
        ),
        TestCase(
            tempo=255,
            speed=1,
            nes_frequency=15,
            rows=16,
            first_highlight=4,
            second_highlight=16,
            expected=(1,) * 16,
        ),
        TestCase(
            tempo=300,
            speed=1,
            nes_frequency=15,
            rows=7,
            first_highlight=4,
            second_highlight=16,
            expected=(1,) * 7,
        ),
        TestCase(
            tempo=50,
            speed=17,
            nes_frequency=300,
            rows=8,
            first_highlight=4,
            second_highlight=16,
            expected=(255,) * 8,
        ),
        TestCase(
            tempo=19,
            speed=31,
            nes_frequency=60,
            rows=8,
            first_highlight=4,
            second_highlight=16,
            expected=(245, 245, 245, 244, 245, 245, 245, 244),
        ),
        TestCase(
            tempo=32,
            speed=31,
            nes_frequency=300,
            rows=8,
            first_highlight=4,
            second_highlight=16,
            expected=(255,) * 8,
        ),
        TestCase(
            tempo=1,
            speed=31,
            nes_frequency=300,
            rows=4,
            first_highlight=4,
            second_highlight=16,
            expected=(255,) * 4,
        ),
        TestCase(
            tempo=1,
            speed=1,
            nes_frequency=300,
            rows=5,
            first_highlight=4,
            second_highlight=16,
            expected=(255,) * 5,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_ticks_match(self, test_case: TestCase) -> None:
        assert test_case.groove.ticks == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_groove_fills_the_pattern(self, test_case: TestCase) -> None:
        assert len(test_case.groove.ticks) == test_case.rows

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_total_and_the_mean_describe_the_rows(self, test_case: TestCase) -> None:
        groove = test_case.groove
        assert groove.total_ticks == sum(groove.ticks)
        assert groove.mean_ticks_per_row == Fraction(groove.total_ticks, test_case.rows)

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_rate_is_reached_as_closely_as_the_range_allows(self, test_case: TestCase) -> None:
        rate = RowRate.from_parameters(
            tempo=test_case.tempo,
            speed=test_case.speed,
            nes_frequency=test_case.nes_frequency,
        )
        reachable = min(max(rate.ticks_per_row, MINIMUM_TICKS), MAXIMUM_TICKS)
        assert abs(test_case.groove.mean_ticks_per_row - reachable) <= Fraction(1, 2 * test_case.rows)

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_every_row_lies_within_the_engine_range(self, test_case: TestCase) -> None:
        assert all(MINIMUM_TICKS <= ticks <= MAXIMUM_TICKS for ticks in test_case.groove.ticks)

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_every_row_neighbours_the_average(self, test_case: TestCase) -> None:
        groove = test_case.groove
        shorter, remainder = divmod(groove.total_ticks, test_case.rows)
        longer = shorter + 1 if remainder else shorter
        assert set(groove.ticks) <= {shorter, longer}

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_longer_rows_come_first(self, test_case: TestCase) -> None:
        groove = test_case.groove
        elapsed = 0
        for index, ticks in enumerate(groove.ticks, start=1):
            elapsed += ticks
            assert elapsed >= groove.total_ticks * index // test_case.rows

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_each_beat_opens_on_its_longest_row(self, test_case: TestCase) -> None:
        ticks = test_case.groove.ticks
        start = 0
        for beats in test_case.metre.spans:
            for beat_rows in beats:
                beat = ticks[start : start + beat_rows]
                assert beat[0] == max(beat)
                start += beat_rows


class TestReferenceCalibration(BaseTestSuite):
    """At the reference tempo and tick rate the speed alone states every row's length."""

    @pytest.mark.parametrize("speed", tuple(range(1, 32)))
    @pytest.mark.parametrize("rows", (1, 2, 7, 16, 60, 64, 256))
    def test_every_row_lasts_speed_ticks(self, speed: int, rows: int) -> None:
        groove = calculate_groove(
            RowRate.from_parameters(
                tempo=REFERENCE_TEMPO,
                speed=speed,
                nes_frequency=REFERENCE_NES_FREQUENCY,
            ),
            Metre(
                rows=rows,
                first_highlight=COMMON_TIME_BEAT,
                second_highlight=COMMON_TIME_BAR,
            ),
            minimum_ticks=MINIMUM_TICKS,
            maximum_ticks=MAXIMUM_TICKS,
        )
        assert groove.ticks == (speed,) * rows
        assert groove.is_uniform


class TestSecondHighlight(BaseTestSuite):
    """The bar organizes where the surplus ticks fall, leaving the tempo to the beat."""

    @staticmethod
    def _groove(rows: int, first_highlight: int, second_highlight: int, tempo: int) -> Groove:
        return calculate_groove(
            RowRate.from_parameters(
                tempo=tempo,
                speed=REFERENCE_SPEED,
                nes_frequency=60,
            ),
            Metre(
                rows=rows,
                first_highlight=first_highlight,
                second_highlight=second_highlight,
            ),
            minimum_ticks=MINIMUM_TICKS,
            maximum_ticks=MAXIMUM_TICKS,
        )

    @pytest.mark.parametrize("second_highlight", (1, 2, 3, 4, 7, 8, 12, 16, 20, 32, 64))
    @pytest.mark.parametrize("rows", (5, 12, 16, 17, 20, 23, 64))
    @pytest.mark.parametrize("tempo", (32, 105, 210, 255))
    def test_the_bar_leaves_the_tempo_alone(self, tempo: int, rows: int, second_highlight: int) -> None:
        grouped = self._groove(rows, COMMON_TIME_BEAT, second_highlight, tempo)
        pattern_wide = self._groove(rows, COMMON_TIME_BEAT, rows, tempo)
        assert grouped.total_ticks == pattern_wide.total_ticks

    def test_a_bar_cutting_across_the_beat_reorganizes_the_groove(self) -> None:
        across = self._groove(4, 2, 3, 105)
        pattern_wide = self._groove(4, 2, 4, 105)
        assert across.ticks == (9, 9, 8, 8)
        assert pattern_wide.ticks == (9, 8, 9, 8)
        assert across.total_ticks == pattern_wide.total_ticks

    def test_a_bar_shorter_than_the_beat_reorganizes_the_groove(self) -> None:
        across = self._groove(5, 5, 4, 105)
        aligned = self._groove(5, 5, 8, 105)
        assert across.ticks == (9, 9, 9, 8, 8)
        assert aligned.ticks == (9, 9, 8, 9, 8)
        assert across.total_ticks == aligned.total_ticks

    def test_a_bar_of_whole_beats_reorganizes_the_groove_too(self) -> None:
        barred = self._groove(64, COMMON_TIME_BEAT, COMMON_TIME_BAR, 105)
        pattern_wide = self._groove(64, COMMON_TIME_BEAT, 64, 105)
        assert barred.ticks == (
            9, 9, 9, 8, 9, 8, 9, 8, 9, 9, 9, 8, 9, 8, 9, 8,
            9, 9, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8,
            9, 9, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8,
            9, 9, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8,
        )  # fmt: skip
        assert pattern_wide.ticks == (
            9, 9, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 9, 9, 8,
            9, 8, 9, 8, 9, 8, 9, 8, 9, 9, 9, 8, 9, 8, 9, 8,
            9, 8, 9, 8, 9, 9, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8,
            9, 9, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8, 9, 8,
        )  # fmt: skip
        assert barred.total_ticks == pattern_wide.total_ticks


class TestGrooveProperties(BaseTestSuite):
    def test_total_ticks_sums_the_rows(self) -> None:
        assert Groove(ticks=(5, 4, 4, 4)).total_ticks == 17

    def test_mean_ticks_per_row_is_exact(self) -> None:
        assert Groove(ticks=(5, 4, 4, 4)).mean_ticks_per_row == Fraction(17, 4)

    def test_a_varying_groove_is_not_uniform(self) -> None:
        assert not Groove(ticks=(5, 4, 4, 4)).is_uniform

    def test_a_constant_groove_is_uniform(self) -> None:
        assert Groove(ticks=(4, 4, 4, 4)).is_uniform

    def test_a_single_row_groove_is_uniform(self) -> None:
        assert Groove(ticks=(4,)).is_uniform
