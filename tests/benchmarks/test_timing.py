from typing import Final

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.performance import song_instructions
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.timing import SONG_TICK_BOUNDS, SongTiming
from tests.suite.performance import make_pulse_reconstruction, place_instrument, project_with_sample
from tests.suite.timing import seconds

ROWS_PER_PATTERN: Final[int] = 64
FRAMES: Final[int] = 32
UNEVEN_TEMPO: Final[int] = 251
SAMPLE_FRAMES: Final[int] = 4
TIMING_SHARE_LIMIT: Final[float] = 0.1


@pytest.fixture(scope="module", name="project")
def project_fixture() -> Project:
    """A song whose row rate never divides into whole ticks, so every frame plans its own bars."""
    project, sample = project_with_sample(
        make_pulse_reconstruction(count=SAMPLE_FRAMES),
        rows_per_pattern=ROWS_PER_PATTERN,
        settings=ProjectSettings(tempo=UNEVEN_TEMPO, speed=6, nes_frequency=60),
    )
    for row_index in range(0, ROWS_PER_PATTERN, 4):
        place_instrument(project, channel_name=ChannelName.PULSE1, row_index=row_index, sample=sample)

    for _ in range(FRAMES - project.song.order_length()):
        project.song.append_frame()

    return project


def _every_row(project: Project) -> int:
    timing = SongTiming.from_project(project, bounds=SONG_TICK_BOUNDS)
    return sum(timing.row_ticks(frame, row) for frame in range(FRAMES) for row in range(ROWS_PER_PATTERN))


class TestTheTimingCostsNextToNothing:
    """A player asks how long a row lasts as it reaches the row, so the answer has to cost a sliver of
    what sounding the row costs.

    The reading is a ratio against the walk that plays the same song into instructions, since what a
    machine walks a song in is its own. What the bound catches is a timing that replans its bars per
    row or walks the song from its start to answer one row.
    """

    def test_every_rows_length_costs_a_sliver_of_the_walk(self, project: Project) -> None:
        lookups = seconds(lambda: _every_row(project))
        walk = seconds(lambda: song_instructions(project))

        assert lookups < walk * TIMING_SHARE_LIMIT, f"lookups {lookups:.4f}s, walk {walk:.4f}s"
