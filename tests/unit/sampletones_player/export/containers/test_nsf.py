from typing import Final

import pytest

from sampletones_core.constants.enums import ALL_CHANNELS
from sampletones_core.exports.format import ExportFormat
from sampletones_player.compression.scheme import CompressionScheme
from sampletones_player.driver.image import DriverImage
from sampletones_player.export.container import ProgramContainer
from sampletones_player.export.containers.nsf import NSFContainer
from sampletones_player.export.program import Program
from sampletones_player.information import ProgramInformation
from sampletones_player.nsf.file import nsf_to_bytes, song_room
from sampletones_player.nsf.header import HEADER_TEXT
from sampletones_player.song import Song
from sampletones_shared.exceptions import SongTooLargeError
from sampletones_shared.paths.extensions import EXT_FILE_NSF
from tests.suite.player import (
    PLAYER_FULL_VOLUME,
    PLAYER_REFERENCE_TIMER,
    player_song,
    pulse_tick,
    resting_streams,
    spelled_song,
)

NTSC_FREQUENCY: Final[int] = 60
PROGRAM: Final[Program] = Program(
    information=ProgramInformation(title="Amen", artist="Author"),
    channels=ALL_CHANNELS,
    loop_tick=None,
    scheme=CompressionScheme.SEARCH,
)
SOUNDING: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_REFERENCE_TIMER)


@pytest.fixture(name="driver", scope="module")
def driver_fixture() -> DriverImage:
    return DriverImage.load()


@pytest.fixture(name="container")
def container_fixture(driver: DriverImage) -> NSFContainer:
    return NSFContainer(driver)


@pytest.fixture(name="song")
def song_fixture() -> Song:
    return player_song(resting_streams((SOUNDING,)), NTSC_FREQUENCY, loop_tick=None)


class TestNSFContainer:
    """What makes a written program an NSF: its format, its extension, its text and its bytes."""

    def test_the_container_stands_where_a_writer_expects_one(self, container: NSFContainer) -> None:
        seam: ProgramContainer = container
        assert seam.export_format == ExportFormat.NSF

    def test_its_files_take_the_nsf_extension(self, container: NSFContainer) -> None:
        assert container.extension == EXT_FILE_NSF

    def test_its_text_has_the_room_of_a_header_field(self, container: NSFContainer) -> None:
        assert container.text == HEADER_TEXT

    def test_the_song_has_the_room_the_driver_leaves(self, container: NSFContainer, driver: DriverImage) -> None:
        assert container.song_room == song_room(driver)

    def test_the_file_is_the_nsf_of_the_song_under_the_programs_text(
        self,
        container: NSFContainer,
        driver: DriverImage,
        song: Song,
    ) -> None:
        assert container.to_bytes(song, PROGRAM) == nsf_to_bytes(song, PROGRAM.information, driver)

    def test_a_song_outgrowing_its_room_is_refused(self, container: NSFContainer) -> None:
        with pytest.raises(SongTooLargeError):
            container.to_bytes(spelled_song(container.song_room, NTSC_FREQUENCY), PROGRAM)
