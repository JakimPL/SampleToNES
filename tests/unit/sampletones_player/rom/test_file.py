from typing import Final

import pytest

from sampletones_core.formats.binary import BinaryReader
from sampletones_player.block.song import song_to_bytes
from sampletones_player.driver.image import DriverImage
from sampletones_player.information import ProgramInformation
from sampletones_player.rom.file import UNWRITTEN_BYTE, rom_to_bytes, song_room
from sampletones_player.rom.header import rom_header
from sampletones_player.shell.image import ShellImage
from sampletones_player.shell.patterns import load_patterns
from sampletones_player.song import Song
from sampletones_player.specification.memory import PROGRAM_SIZE, PROGRAM_START, RESET_VECTOR
from sampletones_player.specification.program import PROGRAM_BLOCK_SIZE
from sampletones_player.specification.rom import ROM_HEADER_SIZE, ROM_MAGIC
from sampletones_player.specification.screen import PATTERNS_SIZE
from sampletones_shared.exceptions import SongTooLargeError
from tests.suite.player import (
    PLAYER_FULL_VOLUME,
    PLAYER_REFERENCE_TIMER,
    player_song,
    pulse_tick,
    resting_streams,
    spelled_song,
)

NTSC_FREQUENCY: Final[int] = 60
INFORMATION: Final[ProgramInformation] = ProgramInformation(title="Amen", artist="Author")
SOUNDING: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_REFERENCE_TIMER)
PROGRAM_OFFSET: Final[int] = ROM_HEADER_SIZE
PATTERNS_OFFSET: Final[int] = ROM_HEADER_SIZE + PROGRAM_SIZE
POWER_ON_VECTOR: Final[int] = 1


@pytest.fixture(name="driver", scope="module")
def driver_fixture() -> DriverImage:
    return DriverImage.load()


@pytest.fixture(name="shell", scope="module")
def shell_fixture() -> ShellImage:
    return ShellImage.load()


@pytest.fixture(name="patterns", scope="module")
def patterns_fixture() -> bytes:
    return load_patterns()


@pytest.fixture(name="song")
def song_fixture() -> Song:
    return player_song(resting_streams((SOUNDING,)), NTSC_FREQUENCY, loop_tick=None)


@pytest.fixture(name="image")
def image_fixture(song: Song, driver: DriverImage, shell: ShellImage, patterns: bytes) -> bytes:
    return rom_to_bytes(song, INFORMATION, driver, shell, patterns)


class TestACartridgeImage:
    """The header, the program a console maps at $8000 and the tiles, in that order."""

    def test_the_song_has_the_room_between_the_driver_and_the_shell(
        self, driver: DriverImage, shell: ShellImage
    ) -> None:
        assert song_room(driver, shell) == shell.start - driver.addresses.song

    def test_it_opens_with_the_header(self, image: bytes) -> None:
        assert image[:ROM_HEADER_SIZE] == rom_header()
        assert image.startswith(ROM_MAGIC)

    def test_it_takes_the_header_the_program_and_the_tiles(self, image: bytes) -> None:
        assert len(image) == ROM_HEADER_SIZE + PROGRAM_SIZE + PATTERNS_SIZE

    def test_the_driver_opens_the_program(self, image: bytes, driver: DriverImage) -> None:
        assert image[PROGRAM_OFFSET : PROGRAM_OFFSET + len(driver.code)] == driver.code

    def test_the_song_follows_the_driver_as_an_nsf_carries_it(
        self, image: bytes, song: Song, driver: DriverImage, shell: ShellImage
    ) -> None:
        block = song_to_bytes(song, song_room(driver, shell))
        start = PROGRAM_OFFSET + len(driver.code)

        assert image[start : start + len(block)] == block

    def test_the_room_the_song_leaves_is_unwritten(
        self, image: bytes, song: Song, driver: DriverImage, shell: ShellImage
    ) -> None:
        start = PROGRAM_OFFSET + len(driver.code) + len(song_to_bytes(song, song_room(driver, shell)))
        end = PROGRAM_OFFSET + shell.start - PROGRAM_START

        assert set(image[start:end]) == {UNWRITTEN_BYTE}

    def test_the_shell_closes_the_program_after_its_block(self, image: bytes, shell: ShellImage) -> None:
        assert (
            image[PATTERNS_OFFSET - len(shell.code) + PROGRAM_BLOCK_SIZE : PATTERNS_OFFSET]
            == shell.code[PROGRAM_BLOCK_SIZE:]
        )

    def test_the_console_starts_in_the_shell(self, image: bytes, shell: ShellImage) -> None:
        offset = PROGRAM_OFFSET + RESET_VECTOR - PROGRAM_START
        assert BinaryReader(image[offset : offset + 2]).read_uint16() == shell.vectors[POWER_ON_VECTOR]

    def test_the_tiles_close_the_file(self, image: bytes, patterns: bytes) -> None:
        assert image[PATTERNS_OFFSET:] == patterns

    def test_a_song_outgrowing_its_room_is_refused(
        self, driver: DriverImage, shell: ShellImage, patterns: bytes
    ) -> None:
        with pytest.raises(SongTooLargeError):
            rom_to_bytes(spelled_song(song_room(driver, shell), NTSC_FREQUENCY), INFORMATION, driver, shell, patterns)
