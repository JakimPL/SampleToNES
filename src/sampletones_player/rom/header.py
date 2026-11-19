from typing import Final

from sampletones_player.specification.driver import LOAD_ADDRESS
from sampletones_player.specification.rom import (
    NROM_MAPPER,
    PADDING_SIZE,
    PATTERN_UNIT_SIZE,
    PROGRAM_UNIT_SIZE,
    ROM_MAGIC,
)
from sampletones_player.specification.screen import PATTERNS_SIZE
from sampletones_player.specification.shell import ADDRESS_SPACE_END

PROGRAM_UNITS: Final[int] = (ADDRESS_SPACE_END - LOAD_ADDRESS) // PROGRAM_UNIT_SIZE
PATTERN_UNITS: Final[int] = PATTERNS_SIZE // PATTERN_UNIT_SIZE
BOARD_FLAGS: Final[int] = NROM_MAPPER
SYSTEM_FLAGS: Final[int] = NROM_MAPPER


def rom_header() -> bytes:
    """The header a cartridge image opens with, stating the plainest board the console has.

    The board carries 32 KB of program and 8 KB of tiles, wired straight to the console, which
    every emulator and flash cartridge plays.
    """
    return ROM_MAGIC + bytes((PROGRAM_UNITS, PATTERN_UNITS, BOARD_FLAGS, SYSTEM_FLAGS)) + bytes(PADDING_SIZE)
