from enum import IntEnum
from typing import Final, FrozenSet, Self

RAM_MIRRORS_END: Final[int] = 0x2000

VIDEO_REGISTERS_START: Final[int] = 0x2000
VIDEO_REGISTERS_END: Final[int] = 0x4000
SPRITE_TRANSFER: Final[int] = 0x4014
FIRST_CONTROLLER: Final[int] = 0x4016
SECOND_CONTROLLER: Final[int] = 0x4017
INPUT_OUTPUT_START: Final[int] = 0x4000
INPUT_OUTPUT_END: Final[int] = 0x4020


class VideoRegister(IntEnum):
    """The eight registers the picture processor answers at, each by its place behind ``$2000``."""

    CONTROL = 0
    MASK = 1
    STATUS = 2
    SPRITE_ADDRESS = 3
    SPRITE_DATA = 4
    SCROLL = 5
    ADDRESS = 6
    DATA = 7

    @classmethod
    def at(cls, address: int) -> Self:
        """The register an address in ``$2000``-``$3FFF`` reaches, the eight repeating through that range."""
        return cls((address - VIDEO_REGISTERS_START) % len(cls))

    @property
    def address(self) -> int:
        """The first address the register answers at."""
        return VIDEO_REGISTERS_START + self.value


WARMED_REGISTERS: Final[FrozenSet[VideoRegister]] = frozenset(
    {
        VideoRegister.CONTROL,
        VideoRegister.MASK,
        VideoRegister.SCROLL,
        VideoRegister.ADDRESS,
    }
)

CONTROL_NAMETABLE_MASK: Final[int] = 0x03
CONTROL_COLUMN_STEP_FLAG: Final[int] = 0x04
CONTROL_INTERRUPT_FLAG: Final[int] = 0x80
MASK_BACKGROUND_FLAG: Final[int] = 0x08
MASK_SPRITES_FLAG: Final[int] = 0x10
MASK_RENDERING: Final[int] = MASK_BACKGROUND_FLAG | MASK_SPRITES_FLAG
STATUS_VERTICAL_BLANK_FLAG: Final[int] = 0x80

VIDEO_MEMORY_SIZE: Final[int] = 0x4000
PATTERN_TABLES_END: Final[int] = 0x2000
NAMETABLES_START: Final[int] = 0x2000
NAMETABLES_SPAN: Final[int] = 0x1000
NAMETABLE_SIZE: Final[int] = 0x0400
NAMETABLE_TILES: Final[int] = 960
NAMETABLE_ATTRIBUTES: Final[int] = NAMETABLE_SIZE - NAMETABLE_TILES
HELD_NAMETABLES: Final[int] = 2
PALETTE_START: Final[int] = 0x3F00
PALETTE_SIZE: Final[int] = 0x20
PALETTE_ENTRY_SIZE: Final[int] = 4
SPRITE_PALETTES_OFFSET: Final[int] = 0x10
COLOR_MASK: Final[int] = 0x3F
SPRITE_MEMORY_SIZE: Final[int] = 0x100
PAGE_SIZE: Final[int] = 0x100

ROW_STEP: Final[int] = 1
COLUMN_STEP: Final[int] = 32

OPEN_BUS: Final[int] = 0x40
CONTROLLER_DATA_MASK: Final[int] = 0x01
