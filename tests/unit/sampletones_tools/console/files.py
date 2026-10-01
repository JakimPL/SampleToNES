from dataclasses import dataclass, field
from typing import Dict, Final, Tuple

from sampletones_core.formats.binary import BinaryWriter
from sampletones_player.specification.nsf import (
    BANKSWITCH_SIZE,
    NSF2_LENGTH_SIZE,
    NSF_MAGIC,
    NSF_VERSION,
    NTSC_PLAY_PERIOD_MICROSECONDS,
    NTSC_REGION,
    PAL_PLAY_PERIOD_MICROSECONDS,
    PROGRAM_START,
    STRING_FIELD_SIZE,
)
from sampletones_tools.console.cartridge import BANK_SIZE

INIT: Final[int] = PROGRAM_START
PLAY: Final[int] = PROGRAM_START + 0x10
LOADED_WHOLE: Final[Tuple[int, ...]] = (0,) * BANKSWITCH_SIZE
ONE_SONG: Final[int] = 1

STORE_ACCUMULATOR: Final[int] = 0x8D
STORE_INDEX: Final[int] = 0x8E
LOAD_IMMEDIATE: Final[int] = 0xA9
LOAD_ABSOLUTE: Final[int] = 0xAD
JUMP: Final[int] = 0x4C
RETURN: Final[int] = 0x60


def absolute(address: int) -> Tuple[int, int]:
    """An operand address as the 6502 stores it, low byte first."""
    return address & 0xFF, address >> 8


@dataclass(frozen=True)
class NSFFile:
    """A small NSF file written for a case: a header and the program bytes placed at their addresses.

    Attributes:
        load: The load address.
        banks: The bank each slot starts with, all zero for a file loaded whole.
        region: The region byte.
        songs: How many songs the header names.
        first_song: The song a player starts with, counted from 1.
        program: The program's bytes, keyed by their offset within the image.
    """

    load: int = PROGRAM_START
    banks: Tuple[int, ...] = LOADED_WHOLE
    region: int = NTSC_REGION
    songs: int = ONE_SONG
    first_song: int = ONE_SONG
    program: Dict[int, Tuple[int, ...]] = field(default_factory=dict)

    @property
    def image(self) -> bytes:
        """The bytes behind the header, each part of the program at its offset and zeros between."""
        size = max((offset + len(code) for offset, code in self.program.items()), default=0)
        image = bytearray(size)
        for offset, code in self.program.items():
            image[offset : offset + len(code)] = bytes(code)

        return bytes(image)

    @property
    def data(self) -> bytes:
        """The whole file, header first."""
        writer = BinaryWriter()
        writer.write_bytes(NSF_MAGIC)
        writer.write_uint8(NSF_VERSION)
        writer.write_uint8(self.songs)
        writer.write_uint8(self.first_song)
        writer.write_uint16(self.load)
        writer.write_uint16(INIT)
        writer.write_uint16(PLAY)
        for text in ("Title", "Artist", "Copyright"):
            writer.write_fixed_string(text, STRING_FIELD_SIZE)

        writer.write_uint16(NTSC_PLAY_PERIOD_MICROSECONDS)
        writer.write_bytes(bytes(self.banks))
        writer.write_uint16(PAL_PLAY_PERIOD_MICROSECONDS)
        writer.write_uint8(self.region)
        writer.write_uint8(0)
        writer.write_uint8(0)
        writer.write_bytes(bytes(NSF2_LENGTH_SIZE))
        writer.write_bytes(self.image)
        return writer.data


def bank_offset(bank: int) -> int:
    """Where a bank starts in an image loaded at the start of ``$8000``."""
    return bank * BANK_SIZE
