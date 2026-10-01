from fractions import Fraction
from itertools import chain
from typing import Final, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.performance import song_instructions
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.timing import SONG_TICK_BOUNDS, Meter, RowRate, SongTiming, TickBounds
from tests.suite.base import BaseTestSuite
from tests.suite.groove import bar_line_drift, bar_rows, is_proportional

ROWS_PER_PATTERN: Final[int] = 4
FRAMES: Final[int] = 3
HALF_TICK: Final[Fraction] = Fraction(1, 2)
COMMON_TIME: Final[Meter] = Meter(rows=16, first_highlight=4, second_highlight=16)
TRACKER_BOUNDS: Final[TickBounds] = TickBounds(minimum=1, maximum=255)
FRAMES_WALKED: Final[int] = 40


def _timing(
    tempo: int,
    speed: int,
    nes_frequency: int,
    meter: Meter,
) -> SongTiming:
    return SongTiming(
        rate=RowRate.from_parameters(tempo=tempo, speed=speed, nes_frequency=nes_frequency),
        meter=meter,
        bounds=SONG_TICK_BOUNDS,
    )


def _song_ticks(timing: SongTiming, frames: int) -> Tuple[int, ...]:
    return tuple(chain.from_iterable(timing.groove(frame).ticks for frame in range(frames)))


@pytest.fixture(name="project")
def project_fixture() -> Project:
    project = Project.create(
        rows_per_pattern=ROWS_PER_PATTERN,
        settings=ProjectSettings(tempo=125, speed=5, nes_frequency=60),
    )
    for _ in range(FRAMES - project.song.order_length()):
        project.song.append_frame()

    return project


class TestFrameTick:
    """A frame starts a bar, so it starts on the tick nearest its exact start."""

    def test_the_first_frame_starts_the_song(self, project: Project) -> None:
        assert SongTiming.from_project(project, bounds=SONG_TICK_BOUNDS).frame_tick(0) == 0

    def test_each_frame_starts_on_the_tick_nearest_its_exact_start(self) -> None:
        """At 30/7 ticks a row, a 16-row pattern lasts 68 4/7 ticks, so frames start 69 or 68 ticks apart."""
        timing = _timing(210, 6, 60, COMMON_TIME)

        assert [timing.frame_tick(frame) for frame in range(8)] == [0, 69, 137, 206, 274, 343, 411, 480]

    def test_the_frame_past_the_last_starts_where_the_walk_ends(self, project: Project) -> None:
        """The song's length and the loop point a frame names are read from one rule."""
        walked = len(song_instructions(project)[ChannelName.PULSE1])

        assert (
            SongTiming.from_project(project, bounds=SONG_TICK_BOUNDS).frame_tick(project.song.order_length()) == walked
        )


class TestTheRemainderCarries:
    """A frame lasts the ticks between its own start and the next frame's, so frames take turns at the surplus."""

    def test_a_frame_after_a_longer_one_is_shorter(self) -> None:
        timing = _timing(210, 6, 60, COMMON_TIME)

        assert timing.groove(0).ticks == (5, 4, 5, 4, 5, 4, 4, 4, 5, 4, 4, 4, 5, 4, 4, 4)
        assert timing.groove(1).ticks == (5, 4, 4, 4, 5, 4, 4, 4, 5, 4, 4, 4, 5, 4, 4, 4)

    def test_the_grooves_repeat_once_the_exact_lengths_add_up_to_a_whole_tick(self) -> None:
        """Seven patterns of 68 4/7 ticks come to 480, so the eighth frame plays the first one's groove."""
        timing = _timing(210, 6, 60, COMMON_TIME)

        assert [timing.groove(frame + 7) for frame in range(7)] == [timing.groove(frame) for frame in range(7)]

    def test_a_rate_of_whole_ticks_plays_every_frame_alike(self) -> None:
        timing = _timing(150, 6, 60, COMMON_TIME)

        assert {timing.groove(frame) for frame in range(FRAMES_WALKED)} == {timing.groove(0)}


class TestRowLookups:
    """Every answer about a row follows from its place in the song alone."""

    @pytest.mark.parametrize("frame", (0, 1, 5, 13))
    def test_a_row_lasts_what_its_frame_groove_gives_it(self, frame: int) -> None:
        timing = _timing(125, 6, 60, Meter(rows=12, first_highlight=3, second_highlight=6))
        groove = timing.groove(frame)

        assert [timing.row_ticks(frame, row) for row in range(12)] == list(groove.ticks)

    @pytest.mark.parametrize("frame", (0, 1, 5, 13))
    def test_a_row_starts_once_every_row_before_it_has_played(self, frame: int) -> None:
        timing = _timing(125, 6, 60, Meter(rows=12, first_highlight=3, second_highlight=6))
        groove = timing.groove(frame)

        for row in range(12):
            assert timing.tick_at(frame, row) == timing.frame_tick(frame) + sum(groove.ticks[:row])


class TestTicksAcross:
    """A span of rows reads each row at its own place, and the order comes round to its first frame."""

    TIMING: Final[SongTiming] = _timing(210, 6, 60, COMMON_TIME)

    def test_a_span_within_a_frame_adds_up_its_rows(self) -> None:
        assert self.TIMING.ticks_across(1, 2, 3, frames=4) == sum(self.TIMING.groove(1).ticks[2:5])

    def test_a_span_into_the_next_frame_reads_that_frame(self) -> None:
        expected = sum(self.TIMING.groove(0).ticks[14:]) + sum(self.TIMING.groove(1).ticks[:2])

        assert self.TIMING.ticks_across(0, 14, 4, frames=4) == expected

    def test_a_span_past_the_song_goes_on_from_its_first_frame(self) -> None:
        expected = sum(self.TIMING.groove(3).ticks[14:]) + sum(self.TIMING.groove(0).ticks[:2])

        assert self.TIMING.ticks_across(3, 14, 4, frames=4) == expected

    def test_a_span_of_whole_passes_lasts_the_song_that_many_times(self) -> None:
        assert self.TIMING.ticks_across(2, 5, 2 * 4 * 16, frames=4) == 2 * self.TIMING.frame_tick(4)

    def test_an_empty_span_lasts_no_tick(self) -> None:
        assert self.TIMING.ticks_across(2, 5, 0, frames=4) == 0


class TestTheBounds:
    """A player holds every row within its own range, and the rate is held there first."""

    def test_a_rate_below_one_tick_plays_every_row_for_one_tick(self) -> None:
        """At tempo 255, speed 1 and 50 Hz a row asks for 25/51 ticks, so the song runs slower than set."""
        timing = _timing(255, 1, 50, COMMON_TIME)

        assert timing.groove(0).ticks == (1,) * 16
        assert timing.frame_tick(FRAMES) == FRAMES * 16

    def test_a_rate_above_a_trackers_range_plays_every_row_at_its_longest(self) -> None:
        timing = SongTiming(
            rate=RowRate.from_parameters(tempo=32, speed=31, nes_frequency=300),
            meter=COMMON_TIME,
            bounds=TRACKER_BOUNDS,
        )

        assert timing.groove(1).ticks == (TRACKER_BOUNDS.maximum,) * 16


SWEPT_METERS: Final[Tuple[Meter, ...]] = (
    COMMON_TIME,
    Meter(rows=16, first_highlight=3, second_highlight=7),
    Meter(rows=12, first_highlight=3, second_highlight=12),
    Meter(rows=20, first_highlight=4, second_highlight=20),
    Meter(rows=24, first_highlight=6, second_highlight=24),
    Meter(rows=16, first_highlight=4, second_highlight=32),
    Meter(rows=16, first_highlight=20, second_highlight=8),
    Meter(rows=16, first_highlight=1, second_highlight=1),
    Meter(rows=1, first_highlight=4, second_highlight=16),
    Meter(rows=7, first_highlight=2, second_highlight=5),
    Meter(rows=256, first_highlight=16, second_highlight=256),
)


def _meter_label(meter: Meter) -> str:
    return f"{meter.rows}r_{meter.first_highlight}_{meter.second_highlight}"


class TestAWholeSongKeepsTheGroovesRules(BaseTestSuite):
    """Over many frames, every bar line stays within half a tick of its exact start and every row in proportion."""

    @pytest.mark.parametrize("meter", SWEPT_METERS, ids=_meter_label)
    @pytest.mark.parametrize("tempo", (32, 97, 125, 133, 210, 251, 255))
    @pytest.mark.parametrize(("speed", "nes_frequency"), ((1, 60), (6, 60), (5, 50), (7, 41), (13, 15), (31, 300)))
    def test_every_bar_line_and_every_row(
        self,
        meter: Meter,
        tempo: int,
        speed: int,
        nes_frequency: int,
    ) -> None:
        timing = _timing(tempo, speed, nes_frequency, meter)
        frames = max(1, FRAMES_WALKED * COMMON_TIME.rows // meter.rows)
        ticks = _song_ticks(timing, frames)

        assert bar_line_drift(ticks, bar_rows(meter, frames), timing.exact_row_ticks) <= HALF_TICK
        assert is_proportional(ticks, timing.exact_row_ticks)
        assert sum(ticks) == timing.frame_tick(frames)
