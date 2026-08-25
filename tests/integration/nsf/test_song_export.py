import struct

import pytest

from sampletones_core.project.project import Project
from sampletones_core.timing import SongTiming
from sampletones_player.builder import song_from_project
from sampletones_player.driver.image import DriverImage
from sampletones_player.nsf.song import song_to_bytes
from sampletones_player.song import Song
from sampletones_player.specification.song import (
    SONG_HEADER_SIZE,
    TOTAL_TICKS_OFFSET,
)
from sampletones_shared.exceptions import SongTooLargeError
from tests.integration.nsf.songs import RECORD_BYTES_PER_TICK, available_bytes


def read_word(data: bytes, offset: int) -> int:
    return int(struct.unpack_from("<H", data, offset)[0])


@pytest.fixture
def project_song(integration_project: Project) -> Song:
    """The song the console plays the integration project's arrangement as."""
    return song_from_project(integration_project, loop_tick=None)


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
        """The block states the whole arrangement, in less room than a record a tick would take."""
        block = song_to_bytes(project_song, available_bytes(driver_image))
        assert read_word(block, TOTAL_TICKS_OFFSET) == project_song.ticks
        assert len(block) < SONG_HEADER_SIZE + RECORD_BYTES_PER_TICK * project_song.ticks


class TestTheProgramAreaBoundsTheSong:
    """A block outgrowing the room behind the driver is named rather than written short."""

    def test_a_song_the_space_cannot_hold_is_refused(
        self,
        project_song: Song,
        driver_image: DriverImage,
    ) -> None:
        """The exporter names the overflow rather than writing a file the console truncates."""
        block = song_to_bytes(project_song, available_bytes(driver_image))

        with pytest.raises(SongTooLargeError):
            song_to_bytes(project_song, len(block) - 1)
