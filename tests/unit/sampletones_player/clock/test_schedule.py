from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Final, Tuple

import pytest
from pydantic import ValidationError

from sampletones_player.clock.schedule import PlaySchedule
from sampletones_player.specification.clock import (
    FIXED_POINT_BITS,
    FIXED_POINT_SCALE,
    MAX_STEP_WHOLE,
    MICROSECONDS_PER_SECOND,
    PLAY_PERIOD_MICROSECONDS,
)
from sampletones_shared.constants.nes import MAX_NES_FREQUENCY, MIN_NES_FREQUENCY
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase

LONG_RUN_PLAY_CALLS: Final[int] = 36000
NES_FREQUENCIES: Final[Tuple[int, ...]] = (15, 24, 25, 30, 50, 60, 100, 120, 200, 299, 300)


def exact_rate(nes_frequency: int) -> Fraction:
    return Fraction(nes_frequency * PLAY_PERIOD_MICROSECONDS, MICROSECONDS_PER_SECOND)


class TestPlaySchedule(BaseTestSuite):
    """One case table, read both for the advances it produces and for the rules they obey."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Tuple[int, ...]
        nes_frequency: int

        @property
        def label(self) -> str:
            return f"{self.nes_frequency}hz"

        @property
        def schedule(self) -> PlaySchedule:
            return PlaySchedule.from_parameters(self.nes_frequency)

    test_cases = (
        TestCase(nes_frequency=60, expected=(0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1)),
        TestCase(nes_frequency=30, expected=(0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0)),
        TestCase(nes_frequency=24, expected=(0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0)),
        TestCase(nes_frequency=15, expected=(0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0)),
        TestCase(nes_frequency=50, expected=(0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0)),
        TestCase(nes_frequency=100, expected=(1, 2, 1, 2, 2, 1, 2, 2, 1, 2, 2, 1)),
        TestCase(nes_frequency=120, expected=(1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2)),
        TestCase(nes_frequency=300, expected=(4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5)),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_advances_match(self, test_case: TestCase) -> None:
        schedule = test_case.schedule
        advances = tuple(schedule.advance_at(play_call) for play_call in range(len(test_case.expected)))
        assert advances == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_advances_sum_to_the_cumulative_count(self, test_case: TestCase) -> None:
        schedule = test_case.schedule
        calls = len(test_case.expected)
        assert sum(schedule.advance_at(play_call) for play_call in range(calls)) == schedule.ticks_at(calls)

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_only_the_floor_and_the_ceiling_appear(self, test_case: TestCase) -> None:
        """Consecutive calls advance by one of two neighbouring amounts, so the stream moves evenly."""
        schedule = test_case.schedule
        advances = {schedule.advance_at(play_call) for play_call in range(LONG_RUN_PLAY_CALLS)}
        assert max(advances) - min(advances) <= 1

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_stream_only_moves_forward(self, test_case: TestCase) -> None:
        schedule = test_case.schedule
        assert all(schedule.advance_at(play_call) >= 0 for play_call in range(LONG_RUN_PLAY_CALLS))


class TestTheScheduleHoldsTheRate(BaseTestSuite):
    """The rate a stream is read at, and the advances a rate dividing the play period produces."""

    @pytest.mark.parametrize("nes_frequency", NES_FREQUENCIES)
    def test_the_rate_is_the_stream_measured_against_the_play_period(self, nes_frequency: int) -> None:
        schedule = PlaySchedule.from_parameters(nes_frequency)
        assert schedule.ticks_per_play_call == exact_rate(nes_frequency)

    def test_a_stream_at_the_play_rate_advances_a_tick_a_call(self) -> None:
        """A stream built at the period the header asks for lands a whole tick on every call."""
        schedule = PlaySchedule(ticks_per_play_call=Fraction(1))
        assert all(schedule.advance_at(play_call) == 1 for play_call in range(LONG_RUN_PLAY_CALLS))

    def test_a_stream_at_half_the_play_rate_alternates(self) -> None:
        schedule = PlaySchedule(ticks_per_play_call=Fraction(1, 2))
        advances = tuple(schedule.advance_at(play_call) for play_call in range(8))
        assert advances == (0, 1, 0, 1, 0, 1, 0, 1)


class TestFixedPointStep(BaseTestSuite):
    """The step the driver carries, and how far its rounding takes the stream from the exact clock."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Tuple[int, int]
        nes_frequency: int

        @property
        def label(self) -> str:
            return f"{self.nes_frequency}hz"

    test_cases = (
        TestCase(nes_frequency=15, expected=(0, 16383)),
        TestCase(nes_frequency=24, expected=(0, 26213)),
        TestCase(nes_frequency=30, expected=(0, 32767)),
        TestCase(nes_frequency=50, expected=(0, 54611)),
        TestCase(nes_frequency=60, expected=(0, 65533)),
        TestCase(nes_frequency=100, expected=(1, 43686)),
        TestCase(nes_frequency=120, expected=(1, 65531)),
        TestCase(nes_frequency=200, expected=(3, 21837)),
        TestCase(nes_frequency=300, expected=(4, 65523)),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_step_fields_match(self, test_case: TestCase) -> None:
        step = PlaySchedule.from_parameters(test_case.nes_frequency).fixed_point_step
        assert (step.whole, step.fraction) == test_case.expected

    @pytest.mark.parametrize("nes_frequency", NES_FREQUENCIES)
    def test_the_value_recomposes_the_fields(self, nes_frequency: int) -> None:
        step = PlaySchedule.from_parameters(nes_frequency).fixed_point_step
        assert divmod(step.value, FIXED_POINT_SCALE) == (step.whole, step.fraction)

    @pytest.mark.parametrize("nes_frequency", NES_FREQUENCIES)
    def test_the_step_is_the_nearest_unit_to_the_exact_rate(self, nes_frequency: int) -> None:
        schedule = PlaySchedule.from_parameters(nes_frequency)
        step = Fraction(schedule.fixed_point_step.value, FIXED_POINT_SCALE)
        assert abs(step - schedule.ticks_per_play_call) <= Fraction(1, 2 * FIXED_POINT_SCALE)

    @pytest.mark.parametrize("nes_frequency", NES_FREQUENCIES)
    def test_the_driver_stays_within_a_tick_of_the_exact_schedule(self, nes_frequency: int) -> None:
        """The claim the whole fixed-point step rests on, held across ten minutes of play calls."""
        schedule = PlaySchedule.from_parameters(nes_frequency)
        assert schedule.maximum_drift(LONG_RUN_PLAY_CALLS) <= 1

    @pytest.mark.parametrize("nes_frequency", NES_FREQUENCIES)
    def test_the_driver_starts_on_the_first_tick(self, nes_frequency: int) -> None:
        schedule = PlaySchedule.from_parameters(nes_frequency)
        assert schedule.ticks_at(0) == 0
        assert schedule.maximum_drift(0) == 0

    @pytest.mark.parametrize("nes_frequency", NES_FREQUENCIES)
    def test_the_accumulator_reaches_the_same_ticks(self, nes_frequency: int) -> None:
        """The driver's own loop, held against the schedule it is written from.

        The schedule multiplies the step by the call count, and the 6502 adds the step to a
        16-bit accumulator once a call and reads the ticks off the carry. Both must count the
        same, since the assembly follows the second and the golden trace follows the first.
        """
        schedule = PlaySchedule.from_parameters(nes_frequency)
        step = schedule.fixed_point_step

        accumulator = 0
        for play_call in range(LONG_RUN_PLAY_CALLS):
            accumulator += step.fraction
            advance = step.whole + (accumulator >> FIXED_POINT_BITS)
            accumulator %= FIXED_POINT_SCALE
            assert advance == schedule.advance_at(play_call)

    def test_a_whole_step_needs_no_fraction(self) -> None:
        step = PlaySchedule(ticks_per_play_call=Fraction(3)).fixed_point_step
        assert (step.whole, step.fraction, step.value) == (3, 0, 3 * FIXED_POINT_SCALE)

    def test_a_step_a_hair_under_a_whole_tick_carries_into_the_whole_byte(self) -> None:
        """Rounding the fraction up spills into the whole byte, keeping both fields in range."""
        rate = Fraction(2) - Fraction(1, 10 * FIXED_POINT_SCALE)
        step = PlaySchedule(ticks_per_play_call=rate).fixed_point_step
        assert (step.whole, step.fraction) == (2, 0)

    def test_the_step_is_derived_once_and_held(self) -> None:
        schedule = PlaySchedule.from_parameters(50)
        assert schedule.fixed_point_step is schedule.fixed_point_step


class TestPlayScheduleBounds(BaseTestSuite):
    def test_the_stream_starts_on_its_first_tick(self) -> None:
        assert PlaySchedule.from_parameters(60).ticks_at(0) == 0

    def test_the_schedule_stays_as_built(self) -> None:
        schedule = PlaySchedule.from_parameters(60)
        with pytest.raises(ValidationError):
            schedule.ticks_per_play_call = Fraction(1)

    @pytest.mark.parametrize("nes_frequency", (MIN_NES_FREQUENCY, MAX_NES_FREQUENCY))
    def test_the_engine_range_fits_the_step(self, nes_frequency: int) -> None:
        step = PlaySchedule.from_parameters(nes_frequency).fixed_point_step
        assert step.whole <= MAX_STEP_WHOLE

    @pytest.mark.parametrize("nes_frequency", (0, -1))
    def test_a_tick_rate_below_one_is_rejected(self, nes_frequency: int) -> None:
        with pytest.raises(ValueError, match="nes_frequency must be at least 1"):
            PlaySchedule.from_parameters(nes_frequency)

    @pytest.mark.parametrize("ticks_per_play_call", (Fraction(0), Fraction(-1, 2)))
    def test_a_stream_that_never_advances_is_rejected(self, ticks_per_play_call: Fraction) -> None:
        with pytest.raises(ValidationError, match="ticks_per_play_call"):
            PlaySchedule(ticks_per_play_call=ticks_per_play_call)

    def test_a_step_past_the_whole_byte_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="ticks_per_play_call"):
            PlaySchedule(ticks_per_play_call=Fraction(MAX_STEP_WHOLE + 1))

    def test_a_negative_call_count_is_rejected(self) -> None:
        schedule = PlaySchedule.from_parameters(60)
        with pytest.raises(ValueError, match="play_calls must be at least 0"):
            schedule.ticks_at(-1)

    def test_a_negative_call_count_is_rejected_by_the_exact_schedule(self) -> None:
        schedule = PlaySchedule.from_parameters(60)
        with pytest.raises(ValueError, match="play_calls must be at least 0"):
            schedule.exact_ticks_at(-1)

    def test_a_negative_run_is_rejected_by_the_drift(self) -> None:
        schedule = PlaySchedule.from_parameters(60)
        with pytest.raises(ValueError, match="play_calls must be at least 0"):
            schedule.maximum_drift(-1)

    def test_a_negative_call_index_is_rejected(self) -> None:
        schedule = PlaySchedule.from_parameters(60)
        with pytest.raises(ValueError, match="play_calls must be at least 0"):
            schedule.advance_at(-1)
