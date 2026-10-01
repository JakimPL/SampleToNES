from typing import Final, List, Optional

from py65.memory import ObservableMemory

from sampletones_player.specification.nsf import PROGRAM_START
from sampletones_tools.console.header import NSFHeader

BANK_SIZE: Final[int] = 0x1000
FIRST_BANK_REGISTER: Final[int] = 0x5FF8
EMPTY_BYTE: Final[int] = 0x00


class Cartridge:
    """The program an NSF file maps into a console's memory, loaded whole or in switched banks.

    A file whose header names no bank loads its image whole at the load address. A banked file is
    cut into 4 KB banks, the image padded at the front by the load address's place within its own
    bank. Writing a bank's number to ``$5FF8`` + slot maps that bank into the slot's 4 KB of
    ``$8000``-``$FFFF``, and the header names the bank every slot starts with.
    """

    def __init__(self, header: NSFHeader, image: bytes) -> None:
        """Holds a file's image as its header says to map it.

        Args:
            header: The file's header.
            image: Everything the file holds behind its header.
        """
        self._header = header
        self._image = image
        self._padded = bytes(header.load % BANK_SIZE) + image

    def mount(self, memory: ObservableMemory) -> None:
        """Maps the program into a console's memory, and switches banks whenever the program asks.

        Args:
            memory: The console's memory.
        """
        if not self._header.banked:
            memory.write(self._header.load, list(self._image))
            return

        for slot, bank in enumerate(self._header.banks):
            self._map(memory, slot, bank)

        def switch(address: int, value: int) -> Optional[int]:
            self._map(memory, address - FIRST_BANK_REGISTER, value)
            return None

        memory.subscribe_to_write(
            range(FIRST_BANK_REGISTER, FIRST_BANK_REGISTER + len(self._header.banks)),
            switch,
        )

    def bank(self, number: int) -> List[int]:
        """The 4 KB a bank holds, the part past the image's end reading as empty bytes.

        Args:
            number: The bank, counted from the front of the padded image.

        Returns:
            List[int]: The bank's bytes.
        """
        start = number * BANK_SIZE
        held = self._padded[start : start + BANK_SIZE]
        return list(held) + [EMPTY_BYTE] * (BANK_SIZE - len(held))

    def _map(
        self,
        memory: ObservableMemory,
        slot: int,
        bank: int,
    ) -> None:
        memory.write(PROGRAM_START + slot * BANK_SIZE, self.bank(bank))
