from typing import Final, FrozenSet

from py65.memory import ObservableMemory

from sampletones_player.specification.memory import PROGRAM_SIZE, PROGRAM_START
from sampletones_player.specification.rom import NROM_MAPPER
from sampletones_shared.exceptions.validation import TruncatedDataError
from sampletones_tools.console.rom.errors import (
    ReadOnlyMemoryError,
    UnsupportedCartridgeError,
)
from sampletones_tools.console.rom.header import Mirroring, ROMHeader

NROM_PROGRAM_UNITS: Final[FrozenSet[int]] = frozenset({1, 2})
NROM_PATTERN_UNITS: Final[int] = 1


class ROMCartridge:
    """An NROM cartridge as a console maps it: a fixed program, and the pattern tables a picture is drawn from.

    The program answers at ``$8000``-``$FFFF``. An image holding 32 KB fills that range, and one
    holding 16 KB answers in both halves of it. The board is plain ROM, so the program is
    read-only throughout, and a store into it is a fault in the program that made it.
    """

    def __init__(self, header: ROMHeader, image: bytes) -> None:
        """Holds a file's image as its header says to map it.

        Args:
            header: The file's header.
            image: Everything the file holds behind its header.

        Raises:
            TruncatedDataError: If the image ends inside its program or its pattern tables.
            UnsupportedCartridgeError: If the header names a board other than NROM with 8 KB of patterns.
        """
        self._header = header
        self._refuse_other_boards()
        held = header.program_size + header.pattern_size
        if len(image) < held:
            raise TruncatedDataError(f"The image holds {len(image)} bytes where its header names {held}")

        self._program = image[: header.program_size]
        self._patterns = image[header.program_size : held]

    @property
    def program(self) -> bytes:
        """The 32 KB the program answers with across ``$8000``-``$FFFF``."""
        return self._program * (PROGRAM_SIZE // len(self._program))

    @property
    def patterns(self) -> bytes:
        """The 8 KB of pattern tables the picture's tiles and sprites are drawn from."""
        return self._patterns

    @property
    def mirroring(self) -> Mirroring:
        """The way the board folds its nametables."""
        return self._header.mirroring

    def mount(self, memory: ObservableMemory) -> None:
        """Maps the program into a console's memory, and refuses every store into it.

        Args:
            memory: The console's memory.
        """
        memory.write(PROGRAM_START, list(self.program))
        memory.subscribe_to_write(range(PROGRAM_START, PROGRAM_START + PROGRAM_SIZE), self._refuse)

    def _refuse_other_boards(self) -> None:
        header = self._header
        if header.mapper != NROM_MAPPER:
            raise UnsupportedCartridgeError(f"The image names mapper {header.mapper}, and the console models NROM")

        if header.trainer or header.alternative_layout:
            raise UnsupportedCartridgeError("The image names a trainer or a nametable layout NROM has no place for")

        if header.program_units not in NROM_PROGRAM_UNITS or header.pattern_units != NROM_PATTERN_UNITS:
            raise UnsupportedCartridgeError(
                f"The image holds {header.program_units} program and {header.pattern_units} pattern units, "
                "where NROM holds one or two of program and one of patterns"
            )

    @staticmethod
    def _refuse(address: int, value: int) -> None:
        raise ReadOnlyMemoryError(f"The program stored {value:#04x} at {address:#06x}, inside the cartridge's ROM")
