from dataclasses import dataclass
from enum import Enum
from typing import Self

from sampletones_core.formats.binary import BinaryReader
from sampletones_player.specification.rom import (
    ALTERNATIVE_LAYOUT_FLAG,
    BATTERY_FLAG,
    MAPPER_HIGH_NIBBLE_MASK,
    MAPPER_NIBBLE_SHIFT,
    PADDING_SIZE,
    PATTERN_UNIT_SIZE,
    PROGRAM_UNIT_SIZE,
    ROM_MAGIC,
    TRAINER_FLAG,
    VERTICAL_MIRRORING_FLAG,
)
from sampletones_tools.console.rom.errors import NotAROMError


class Mirroring(Enum):
    """How a board folds the four nametables the picture addresses onto the two it holds."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


@dataclass(frozen=True)
class ROMHeader:
    """What a console reads from an iNES header before it maps the image.

    Attributes:
        program_units: How many 16 KB units of program the image holds.
        pattern_units: How many 8 KB units of pattern tables the image holds.
        board: The byte naming the board's wiring: mirroring, battery, trainer, and the mapper's low half.
        system: The byte naming the console family, and the mapper's high half.
    """

    program_units: int
    pattern_units: int
    board: int
    system: int

    @classmethod
    def read(cls, data: bytes) -> Self:
        """Reads the header at the front of a whole cartridge image, field by field as the format lays them out.

        Args:
            data: The file, header first.

        Returns:
            Self: The header.

        Raises:
            NotAROMError: If the file opens with something other than the iNES signature.
            TruncatedDataError: If the file ends inside the header.
        """
        reader = BinaryReader(data)
        signature = reader.read_bytes(len(ROM_MAGIC))
        if signature != ROM_MAGIC:
            raise NotAROMError(f"The file opens with {signature!r}, not the iNES signature {ROM_MAGIC!r}")

        program_units = reader.read_uint8()
        pattern_units = reader.read_uint8()
        board = reader.read_uint8()
        system = reader.read_uint8()
        reader.skip(PADDING_SIZE)
        return cls(
            program_units=program_units,
            pattern_units=pattern_units,
            board=board,
            system=system,
        )

    @property
    def program_size(self) -> int:
        """The bytes of program the image holds behind its header."""
        return self.program_units * PROGRAM_UNIT_SIZE

    @property
    def pattern_size(self) -> int:
        """The bytes of pattern tables the image holds behind its program."""
        return self.pattern_units * PATTERN_UNIT_SIZE

    @property
    def mapper(self) -> int:
        """The board's number, its low half read from the board byte and its high half from the system byte."""
        return (self.system & MAPPER_HIGH_NIBBLE_MASK) | (self.board >> MAPPER_NIBBLE_SHIFT)

    @property
    def mirroring(self) -> Mirroring:
        """The way the board folds its nametables."""
        return Mirroring.VERTICAL if self.board & VERTICAL_MIRRORING_FLAG else Mirroring.HORIZONTAL

    @property
    def battery(self) -> bool:
        """Whether the board keeps memory on a battery."""
        return bool(self.board & BATTERY_FLAG)

    @property
    def trainer(self) -> bool:
        """Whether 512 bytes of trainer stand between the header and the program."""
        return bool(self.board & TRAINER_FLAG)

    @property
    def alternative_layout(self) -> bool:
        """Whether the board lays its nametables out its own way, as a four-screen board does."""
        return bool(self.board & ALTERNATIVE_LAYOUT_FLAG)
