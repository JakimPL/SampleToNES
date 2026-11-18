from dataclasses import dataclass
from typing import Final, Optional

import pytest

from sampletones_player.rom.clock import ClockDigits, ProgramClock, clock_digits, frames_until
from sampletones_player.specification.clock import FIXED_POINT_SCALE
from sampletones_player.specification.program import LONGEST_SHOWN_SECONDS, NO_LOOP_FRAMES, PROGRESS_PIXELS, SECOND_STEP
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.player import PLAYER_FULL_VOLUME, PLAYER_REFERENCE_TIMER, player_song, pulse_tick, resting_streams

HALF_TICK: Final[int] = FIXED_POINT_SCALE // 2
WHOLE_TICK: Final[int] = FIXED_POINT_SCALE
TOTAL_FRAMES: Final[int] = 1800
LOOP_FRAME: Final[int] = 600
SOUNDING: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_REFERENCE_TIMER)


class TestFramesUntilATick(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        tick: int
        step: int
        expected: int

    test_cases = (
        TestCase(tick=0, step=WHOLE_TICK, expected=0, label="the first tick stands from the start"),
        TestCase(tick=5, step=WHOLE_TICK, expected=5, label="a tick a frame"),
        TestCase(tick=5, step=HALF_TICK, expected=10, label="a tick every two frames"),
        TestCase(tick=5, step=3 * WHOLE_TICK, expected=2, label="three ticks a frame reach past the tick"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_first_frame_standing_on_the_tick(self, test_case: TestCase) -> None:
        assert frames_until(test_case.tick, test_case.step) == test_case.expected


class TestClockDigits(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        seconds: int
        expected: ClockDigits

    test_cases = (
        TestCase(seconds=0, expected=(0, 0, 0, 0), label="no time"),
        TestCase(seconds=225, expected=(0, 3, 4, 5), label="minutes and seconds"),
        TestCase(seconds=LONGEST_SHOWN_SECONDS, expected=(9, 9, 5, 9), label="the longest time shown"),
        TestCase(seconds=LONGEST_SHOWN_SECONDS + 1, expected=(9, 9, 5, 9), label="beyond it"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_digits_of_a_time(self, test_case: TestCase) -> None:
        assert clock_digits(test_case.seconds) == test_case.expected


class TestAProgramClock(BaseTestSuite):
    @staticmethod
    def clock(loop_frame: Optional[int]) -> ProgramClock:
        return ProgramClock(total_frames=TOTAL_FRAMES, loop_frame=loop_frame)

    def test_the_progress_bar_fills_by_the_song_s_end_and_no_further(self) -> None:
        filled = TOTAL_FRAMES * self.clock(None).progress_step

        assert filled <= PROGRESS_PIXELS * FIXED_POINT_SCALE
        assert filled > (PROGRESS_PIXELS - 1) * FIXED_POINT_SCALE

    def test_a_song_that_ends_counts_no_loop(self) -> None:
        assert self.clock(None).loop_frames == NO_LOOP_FRAMES

    def test_a_repeating_song_counts_the_frames_from_its_loop_to_its_end(self) -> None:
        assert self.clock(LOOP_FRAME).loop_frames == TOTAL_FRAMES - LOOP_FRAME

    def test_a_loop_shorter_than_a_frame_still_counts_one(self) -> None:
        assert self.clock(TOTAL_FRAMES).loop_frames == NO_LOOP_FRAMES + 1

    def test_the_total_time_is_what_the_frames_add_up_to(self) -> None:
        seconds = TOTAL_FRAMES * SECOND_STEP // FIXED_POINT_SCALE

        assert self.clock(None).total_time == clock_digits(seconds)

    def test_the_loop_resumes_the_clock_where_the_frames_put_it(self) -> None:
        clock = self.clock(LOOP_FRAME)
        counted = LOOP_FRAME * SECOND_STEP

        assert clock.loop_time == clock_digits(counted // FIXED_POINT_SCALE)
        assert clock.loop_second == counted % FIXED_POINT_SCALE
        assert clock.loop_progress == LOOP_FRAME * clock.progress_step

    def test_a_song_is_measured_by_its_own_schedule(self) -> None:
        song = player_song(resting_streams((SOUNDING,) * 6), 30, loop_tick=3)

        clock = ProgramClock.of(song)

        step = song.schedule.fixed_point_step.value
        assert clock.total_frames == frames_until(song.ticks, step)
        assert clock.loop_frame == frames_until(3, step)
