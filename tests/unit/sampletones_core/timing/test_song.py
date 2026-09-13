from typing import Final

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.performance import song_instructions
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.timing import SongTiming

ROWS_PER_PATTERN: Final[int] = 4
FRAMES: Final[int] = 3


@pytest.fixture(name="project")
def project_fixture() -> Project:
    project = Project.create(
        rows_per_pattern=ROWS_PER_PATTERN,
        settings=ProjectSettings(tempo=150, speed=5, nes_frequency=60),
    )
    for _ in range(FRAMES - project.song.order_length()):
        project.song.append_frame()

    return project


class TestFrameTick:
    """The tick an order frame starts on, read from the groove each frame lasts."""

    def test_the_first_frame_starts_the_song(self, project: Project) -> None:
        assert SongTiming.from_project(project).frame_tick(0) == 0

    def test_each_frame_starts_one_groove_after_the_one_before(self, project: Project) -> None:
        timing = SongTiming.from_project(project)
        groove = timing.groove().total_ticks
        assert [timing.frame_tick(frame) for frame in range(FRAMES)] == [groove * frame for frame in range(FRAMES)]

    def test_the_frame_past_the_last_starts_where_the_walk_ends(self, project: Project) -> None:
        """The song's length and the loop point a frame names are read from one rule."""
        walked = len(song_instructions(project)[ChannelName.PULSE1])
        assert SongTiming.from_project(project).frame_tick(project.song.order_length()) == walked
