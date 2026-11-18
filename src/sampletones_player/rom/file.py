from typing import Final

from sampletones_player.block.song import song_to_bytes
from sampletones_player.driver.image import DriverImage
from sampletones_player.information import ProgramInformation
from sampletones_player.rom.clock import ProgramClock
from sampletones_player.rom.header import rom_header
from sampletones_player.rom.program import program_block
from sampletones_player.shell.image import ShellImage
from sampletones_player.song import Song

UNWRITTEN_BYTE: Final[int] = 0xFF


def song_room(driver: DriverImage, shell: ShellImage) -> int:
    """The bytes a cartridge leaves the song: everything between the driver and the shell."""
    return shell.start - driver.addresses.song


def rom_to_bytes(
    song: Song,
    information: ProgramInformation,
    driver: DriverImage,
    shell: ShellImage,
    patterns: bytes,
) -> bytes:
    """Builds the bytes of a cartridge image: the header, the program and the tiles.

    The driver and the song sit exactly where an NSF puts them, the shell closes the program at
    the top of the address space, and the room between them is left unwritten.

    Args:
        song: The streams, the clock and the loop point to play.
        information: The text the screen shows the program under.
        driver: The assembled driver the cartridge carries.
        shell: The assembled shell the cartridge carries.
        patterns: The tiles the screen and its sprites are drawn with.

    Returns:
        bytes: The whole file.

    Raises:
        SongTooLargeError: If the song takes more room than the driver and the shell leave it.
        ValueError: If the shell was built with another driver.
    """
    room = song_room(driver, shell)
    data = song_to_bytes(song, room)
    block = program_block(driver.addresses.song, information, ProgramClock.of(song))
    program = driver.code + data + bytes([UNWRITTEN_BYTE]) * (room - len(data)) + shell.with_program(block)
    return rom_header() + program + patterns
