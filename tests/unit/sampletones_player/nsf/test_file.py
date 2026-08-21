import struct
from pathlib import Path
from typing import Final

import pytest

from sampletones_player.driver.image import DriverImage
from sampletones_player.nsf.file import nsf_to_bytes, write_nsf
from sampletones_player.nsf.header import header_to_bytes
from sampletones_player.nsf.information import NSFInformation
from sampletones_player.nsf.song import song_to_bytes
from sampletones_player.song import Song
from sampletones_player.specification.nsf import (
    HEADER_SIZE,
    LOAD_ADDRESS_OFFSET,
    PROGRAM_SIZE,
)
from sampletones_shared.exceptions import SongTooLargeError
from tests.suite.player import (
    PLAYER_FULL_VOLUME,
    PLAYER_REFERENCE_TIMER,
    PLAYER_SILENT_VOLUME,
    player_song,
    pulse_tick,
    resting_streams,
)

NTSC_FREQUENCY: Final[int] = 60
FILENAME: Final[str] = "song.nsf"
INFORMATION: Final[NSFInformation] = NSFInformation(title="Amen", artist="Jakim")

SOUNDING: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_REFERENCE_TIMER)
RESTING: Final = pulse_tick(PLAYER_SILENT_VOLUME, 0, PLAYER_REFERENCE_TIMER)


@pytest.fixture(scope="module")
def image() -> DriverImage:
    return DriverImage.load()


@pytest.fixture
def song() -> Song:
    return player_song(resting_streams((SOUNDING, RESTING)), NTSC_FREQUENCY, loop_tick=None)


def oversized_song(image: DriverImage) -> Song:
    ticks = PROGRAM_SIZE - len(image.code)
    return player_song(resting_streams((SOUNDING,) * ticks), NTSC_FREQUENCY, loop_tick=None)


class TestNSFBytes:
    """The three parts a console loads, in the order it loads them."""

    def test_the_file_leads_with_its_header(self, song: Song, image: DriverImage) -> None:
        assert nsf_to_bytes(song, INFORMATION, image)[:HEADER_SIZE] == header_to_bytes(INFORMATION, image.addresses)

    def test_the_driver_follows_the_header(self, song: Song, image: DriverImage) -> None:
        assert nsf_to_bytes(song, INFORMATION, image)[HEADER_SIZE : HEADER_SIZE + len(image.code)] == image.code

    def test_the_song_follows_the_driver(self, song: Song, image: DriverImage) -> None:
        data = nsf_to_bytes(song, INFORMATION, image)
        assert data[HEADER_SIZE + len(image.code) :] == song_to_bytes(song, PROGRAM_SIZE - len(image.code))

    def test_the_file_is_its_three_parts_and_nothing_more(self, song: Song, image: DriverImage) -> None:
        block = song_to_bytes(song, PROGRAM_SIZE - len(image.code))
        assert len(nsf_to_bytes(song, INFORMATION, image)) == HEADER_SIZE + len(image.code) + len(block)

    def test_the_loaded_image_fits_the_program_area(self, song: Song, image: DriverImage) -> None:
        assert len(nsf_to_bytes(song, INFORMATION, image)) - HEADER_SIZE <= PROGRAM_SIZE

    def test_the_header_loads_the_image_where_the_driver_expects_it(
        self,
        song: Song,
        image: DriverImage,
    ) -> None:
        data = nsf_to_bytes(song, INFORMATION, image)
        assert struct.unpack_from("<H", data, LOAD_ADDRESS_OFFSET)[0] == image.addresses.load

    def test_the_song_lands_at_the_address_the_driver_reads_it_from(
        self,
        song: Song,
        image: DriverImage,
    ) -> None:
        data = nsf_to_bytes(song, INFORMATION, image)
        block = song_to_bytes(song, PROGRAM_SIZE - len(image.code))
        song_start = len(data) - len(block)
        assert image.addresses.load + song_start - HEADER_SIZE == image.addresses.song


class TestSongsBeyondTheProgramArea:
    """A song outgrowing the room behind the driver names the overflow."""

    def test_a_song_too_large_for_the_program_area_raises(self, image: DriverImage) -> None:
        with pytest.raises(SongTooLargeError):
            nsf_to_bytes(oversized_song(image), INFORMATION, image)


class TestWriteNSF:
    """The bytes reaching a file on disk."""

    def test_the_file_holds_the_bytes_the_song_serialises_to(
        self,
        song: Song,
        image: DriverImage,
        tmp_path: Path,
    ) -> None:
        destination = tmp_path / FILENAME
        write_nsf(destination, song, INFORMATION, image)
        assert destination.read_bytes() == nsf_to_bytes(song, INFORMATION, image)
