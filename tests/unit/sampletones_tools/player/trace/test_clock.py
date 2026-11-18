from dataclasses import dataclass, replace
from typing import Final, List, Optional, Tuple

import pytest

from sampletones_player.rom.clock import ProgramClock, clock_digits
from sampletones_player.specification.binary import BYTE_VALUES
from sampletones_player.specification.clock import FIXED_POINT_SCALE
from sampletones_player.specification.program import LONGEST_SHOWN_SECONDS, PROGRESS_PIXELS
from sampletones_tools.player.trace.clock import CartridgeClock
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

TOTAL_FRAMES: Final[int] = 400
LOOP_FRAME: Final[int] = 150
ROUNDS: Final[int] = 3
SHIMMER_FRAMES: Final[int] = 8
LAST_FRACTION: Final[int] = FIXED_POINT_SCALE - 1


def clock_run(program: ProgramClock, frames: int) -> List[CartridgeClock]:
    """The clock at the start and after each of ``frames`` played frames."""
    clocks = [CartridgeClock.started(program)]
    for _ in range(frames):
        clocks.append(clocks[-1].advanced())

    return clocks


def reading(clock: CartridgeClock) -> Tuple[int, int, int]:
    """What the screen shows of a clock and what it carries to the next frame: the time, its fraction and the bar."""
    return clock.seconds, clock.second_fraction, clock.progress


@pytest.fixture(name="ending")
def ending_fixture() -> ProgramClock:
    return ProgramClock(total_frames=TOTAL_FRAMES, loop_frame=None)


@pytest.fixture(name="looping")
def looping_fixture() -> ProgramClock:
    return ProgramClock(total_frames=TOTAL_FRAMES, loop_frame=LOOP_FRAME)


class TestTheClockCountsPlayedFrames:
    def test_a_song_starts_at_zero_with_every_frame_to_count(self, ending: ProgramClock) -> None:
        clock = CartridgeClock.started(ending)

        assert (clock.remaining, clock.seconds, clock.progress_pixels, clock.played_frames) == (TOTAL_FRAMES, 0, 0, 0)
        assert not clock.ended

    def test_the_clock_shows_the_seconds_the_frames_add_up_to(self, ending: ProgramClock) -> None:
        clocks = clock_run(ending, TOTAL_FRAMES)

        assert [clock.seconds for clock in clocks] == [ProgramClock.seconds_at(frames) for frames in range(len(clocks))]

    def test_the_bar_grows_by_the_program_s_step(self, ending: ProgramClock) -> None:
        clocks = clock_run(ending, TOTAL_FRAMES)

        assert [clock.progress for clock in clocks] == [frames * ending.progress_step for frames in range(len(clocks))]

    def test_the_noise_shape_turns_every_two_frames(self, ending: ProgramClock) -> None:
        clocks = clock_run(ending, SHIMMER_FRAMES)

        assert [clock.shimmer for clock in clocks[1:]] == [False, True, True, False, False, True, True, False]

    def test_the_frame_count_takes_one_byte(self, ending: ProgramClock) -> None:
        assert CartridgeClock.after(ending, BYTE_VALUES + 1).played_frames == 1

    def test_the_digits_roll_over_past_the_longest_time_they_show(self, ending: ProgramClock) -> None:
        clock = replace(CartridgeClock.started(ending), seconds=LONGEST_SHOWN_SECONDS, second_fraction=LAST_FRACTION)

        assert clock.advanced().seconds == 0

    def test_a_negative_count_of_frames_is_refused(self, ending: ProgramClock) -> None:
        with pytest.raises(ValueError):
            CartridgeClock.after(ending, -1)


class TestASongThatEnds:
    """The clock runs to the song's last frame and holds there, the transport turning to STOP."""

    def test_the_song_ends_on_its_last_frame(self, ending: ProgramClock) -> None:
        clocks = clock_run(ending, TOTAL_FRAMES)

        assert [clock.ended for clock in clocks].index(True) == TOTAL_FRAMES

    def test_the_clock_holds_once_the_song_has_ended(self, ending: ProgramClock) -> None:
        last = CartridgeClock.after(ending, TOTAL_FRAMES)

        assert CartridgeClock.after(ending, TOTAL_FRAMES + ROUNDS) == last

    def test_the_clock_shows_the_song_s_whole_length(self, ending: ProgramClock) -> None:
        last = CartridgeClock.after(ending, TOTAL_FRAMES)

        assert clock_digits(last.seconds) == ending.total_time

    def test_the_bar_fills_to_its_last_pixel_by_the_song_s_end(self, ending: ProgramClock) -> None:
        last = CartridgeClock.after(ending, TOTAL_FRAMES)

        assert PROGRESS_PIXELS - 1 <= last.progress_pixels <= PROGRESS_PIXELS

    def test_the_noise_shape_holds_its_turn_once_the_song_has_ended(self, ending: ProgramClock) -> None:
        last = CartridgeClock.after(ending, TOTAL_FRAMES)

        assert last.played_frames == TOTAL_FRAMES % BYTE_VALUES
        assert CartridgeClock.after(ending, TOTAL_FRAMES + ROUNDS).shimmer == last.shimmer


class TestASongThatComesRound:
    """Where the frames run out, the clock takes up the figures its loop starts from and counts the loop again."""

    def test_the_clock_never_ends(self, looping: ProgramClock) -> None:
        clocks = clock_run(looping, TOTAL_FRAMES + ROUNDS * looping.loop_frames)

        assert not any(clock.ended for clock in clocks)

    def test_the_clock_comes_round_to_where_the_loop_stood(self, looping: ProgramClock) -> None:
        first_pass = clock_run(looping, TOTAL_FRAMES)
        repeated = clock_run(looping, TOTAL_FRAMES + ROUNDS * looping.loop_frames)[TOTAL_FRAMES:]

        loop = [reading(clock) for clock in first_pass[LOOP_FRAME:TOTAL_FRAMES]]
        assert [reading(clock) for clock in repeated] == (loop * (ROUNDS + 1))[: len(repeated)]

    def test_the_count_starts_again_with_the_loop_s_frames(self, looping: ProgramClock) -> None:
        assert CartridgeClock.after(looping, TOTAL_FRAMES).remaining == looping.loop_frames

    def test_the_frame_count_runs_on_through_the_loop(self, looping: ProgramClock) -> None:
        frames = TOTAL_FRAMES + looping.loop_frames

        assert CartridgeClock.after(looping, frames).played_frames == frames % BYTE_VALUES


class TestTheProgressBarStaysWithinItsWidth(BaseTestSuite):
    """The bar fills as the song ends, and a loop takes it back before it passes its last pixel."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        total_frames: int
        loop_frame: Optional[int]

    test_cases = (
        TestCase(total_frames=TOTAL_FRAMES, loop_frame=None, label="a song that ends"),
        TestCase(total_frames=TOTAL_FRAMES, loop_frame=LOOP_FRAME, label="a song that comes round"),
        TestCase(total_frames=7, loop_frame=None, label="a song of a few frames"),
        TestCase(total_frames=7, loop_frame=7, label="a loop shorter than a frame"),
        TestCase(total_frames=PROGRESS_PIXELS + 1, loop_frame=0, label="a song a frame longer than the bar"),
        TestCase(total_frames=3 * PROGRESS_PIXELS - 1, loop_frame=None, label="a song slower than the bar"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_bar_never_passes_its_width(self, test_case: TestCase) -> None:
        program = ProgramClock(total_frames=test_case.total_frames, loop_frame=test_case.loop_frame)
        clocks = clock_run(program, ROUNDS * test_case.total_frames)

        assert max(clock.progress_pixels for clock in clocks) <= PROGRESS_PIXELS
