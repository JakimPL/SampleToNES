from typing import Final

import pytest

from sampletones_core.project.project import Project
from sampletones_core.timing import SongTiming
from sampletones_player.builder import song_from_project
from sampletones_player.driver.image import DriverImage
from sampletones_player.nsf.song import song_to_bytes
from sampletones_player.song import Song
from sampletones_player.specification.nsf import PROGRAM_SIZE
from sampletones_player.specification.song import SONG_HEADER_SIZE
from sampletones_shared.exceptions import SongTooLargeError
from sampletones_shared.music import Tuning

RECORD_BYTES_PER_TICK: Final[int] = 11


def available_bytes(driver_image: DriverImage) -> int:
    """The program area the song block is written into, behind the driver."""
    return PROGRAM_SIZE - len(driver_image.code)


def lengthened(project: Project, frames: int) -> Project:
    """``project`` with its order repeated to ``frames`` positions, over the same samples.

    The song is copied rather than edited so the session's own project keeps the arrangement
    every other case reads.
    """
    longer = Project.create(
        rows_per_pattern=project.song.rows_per_pattern,
        settings=project.settings,
    )
    for sample in project.samples:
        longer.samples.append(sample)

    longer.song = project.song.model_copy(deep=True)
    while longer.song.order_length() < frames:
        longer.song.duplicate_frame(longer.song.order_length() - 1)

    return longer


@pytest.fixture
def project_song(integration_project: Project) -> Song:
    """The song the console plays the integration project's arrangement as."""
    return song_from_project(integration_project, Tuning(), loop_tick=None)


class TestTheProjectReachesTheConsole:
    """A whole arrangement flattened into the streams the driver already plays."""

    def test_the_song_lasts_the_ticks_the_projects_groove_gives_its_order(
        self,
        integration_project: Project,
        project_song: Song,
    ) -> None:
        groove = SongTiming.from_project(integration_project).groove()
        assert project_song.ticks == integration_project.song.order_length() * groove.total_ticks

    def test_every_channel_the_order_plays_sounds(self, project_song: Song) -> None:
        """The fixture's arrangement fills all four channels, so none of them rests throughout."""
        for stream in (
            project_song.streams.pulse1,
            project_song.streams.pulse2,
            project_song.streams.triangle,
            project_song.streams.noise,
        ):
            assert len(set(stream)) > 1

    def test_the_arrangement_writes_through_the_song_block(
        self,
        project_song: Song,
        driver_image: DriverImage,
    ) -> None:
        block = song_to_bytes(project_song, available_bytes(driver_image))
        assert len(block) == SONG_HEADER_SIZE + RECORD_BYTES_PER_TICK * project_song.ticks


class TestTheProgramAreaBoundsTheSong:
    """Where a record per tick stops fitting behind the driver."""

    def test_a_song_outgrowing_the_program_area_is_refused(
        self,
        integration_project: Project,
        driver_image: DriverImage,
    ) -> None:
        """The exporter names the overflow rather than writing a file the console truncates."""
        space = available_bytes(driver_image)
        groove = SongTiming.from_project(integration_project).groove()
        frames = space // (RECORD_BYTES_PER_TICK * groove.total_ticks) + 2
        song = song_from_project(lengthened(integration_project, frames), Tuning(), loop_tick=None)

        with pytest.raises(SongTooLargeError):
            song_to_bytes(song, space)
