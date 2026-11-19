from typing import Dict, Final, Sequence, Tuple

from sampletones_tools.console.rom.errors import ReadOnlyMemoryError
from sampletones_tools.console.rom.header import Mirroring
from sampletones_tools.console.rom.registers import (
    COLOR_MASK,
    COLUMN_STEP,
    CONTROL_COLUMN_STEP_FLAG,
    CONTROL_INTERRUPT_FLAG,
    CONTROL_NAMETABLE_MASK,
    HELD_NAMETABLES,
    MASK_RENDERING,
    NAMETABLE_SIZE,
    NAMETABLE_TILES,
    NAMETABLES_SPAN,
    NAMETABLES_START,
    PALETTE_ENTRY_SIZE,
    PALETTE_SIZE,
    PALETTE_START,
    PATTERN_TABLES_END,
    ROW_STEP,
    SPRITE_MEMORY_SIZE,
    SPRITE_PALETTES_OFFSET,
    STATUS_VERTICAL_BLANK_FLAG,
    VIDEO_MEMORY_SIZE,
    WARMED_REGISTERS,
    VideoRegister,
)
from sampletones_tools.console.rom.screen import Screen

NAMETABLE_FOLDS: Final[Dict[Mirroring, Tuple[int, int, int, int]]] = {
    Mirroring.HORIZONTAL: (0, 0, 1, 1),
    Mirroring.VERTICAL: (0, 1, 0, 1),
}

COARSE_X_MASK: Final[int] = 0x001F
COARSE_Y_MASK: Final[int] = 0x03E0
COARSE_Y_SHIFT: Final[int] = 5
NAMETABLE_SELECT_MASK: Final[int] = 0x0C00
NAMETABLE_SELECT_SHIFT: Final[int] = 10
FINE_Y_MASK: Final[int] = 0x7000
FINE_Y_SHIFT: Final[int] = 12
FINE_MASK: Final[int] = 0x07
FINE_BITS: Final[int] = 3
ADDRESS_HIGH_MASK: Final[int] = 0x3F
ADDRESS_HIGH_SHIFT: Final[int] = 8
ADDRESS_LOW_MASK: Final[int] = 0x00FF
ADDRESS_MASK: Final[int] = 0x7FFF
UNWRITTEN: Final[int] = 0x00


class Video:
    """The picture processor as a program meets it: eight registers, and the memory behind them.

    The model holds what a program can leave there and read back. The scroll and address
    registers share the latch and the pending address the hardware shares between them, so a
    program that writes an address and leaves the scroll standing where that address put it shows
    in :attr:`screen`. The pattern tables are the cartridge's ROM, and a store into them is a
    fault in the program that made it.

    Drawing itself stays outside the model: it sets the vertical blank flag when told a frame
    begins, clears it when read or told the blank ends, and holds the sprite and nametable bytes
    for whoever renders them. The sprite-zero and overflow flags read as clear throughout, and a
    register that only takes stores reads as zero.

    For a stretch after power-on the hardware ignores its control, mask, scroll and address
    registers, and the model ignores them until :meth:`finish_warming` is called.
    """

    def __init__(self, patterns: bytes, mirroring: Mirroring) -> None:
        """Builds the processor over a cartridge's pattern tables.

        Args:
            patterns: The 8 KB the cartridge holds at ``$0000``-``$1FFF`` of video memory.
            mirroring: The way the board folds the four nametables onto the two it holds.
        """
        self._patterns = patterns
        self._fold = NAMETABLE_FOLDS[mirroring]
        self._nametables = bytearray(HELD_NAMETABLES * NAMETABLE_SIZE)
        self._palette = bytearray(PALETTE_SIZE)
        self._sprites = bytearray(SPRITE_MEMORY_SIZE)
        self._control = UNWRITTEN
        self._mask = UNWRITTEN
        self._vertical_blank = False
        self._warming = True
        self._interrupt_due = False
        self._latched = False
        self._pending = UNWRITTEN
        self._address = UNWRITTEN
        self._fine_x = UNWRITTEN
        self._buffered = UNWRITTEN
        self._sprite_address = UNWRITTEN

    @property
    def rendering(self) -> bool:
        """Whether the mask register has the background or the sprites drawn."""
        return bool(self._mask & MASK_RENDERING)

    @property
    def interrupts(self) -> bool:
        """Whether the control register asks for an interrupt at every vertical blank."""
        return bool(self._control & CONTROL_INTERRUPT_FLAG)

    @property
    def vertical_blank(self) -> bool:
        """Whether the vertical blank flag stands, set by a frame beginning and cleared by a status read."""
        return self._vertical_blank

    @property
    def warming(self) -> bool:
        """Whether the processor still ignores its control, mask, scroll and address registers."""
        return self._warming

    @property
    def screen(self) -> Screen:
        """What the processor holds for the picture it draws next."""
        table = self._fold[(self._pending & NAMETABLE_SELECT_MASK) >> NAMETABLE_SELECT_SHIFT] * NAMETABLE_SIZE
        held = bytes(self._nametables[table : table + NAMETABLE_SIZE])
        coarse_x = self._pending & COARSE_X_MASK
        coarse_y = (self._pending & COARSE_Y_MASK) >> COARSE_Y_SHIFT
        fine_y = (self._pending & FINE_Y_MASK) >> FINE_Y_SHIFT
        return Screen(
            nametable=held[:NAMETABLE_TILES],
            attributes=held[NAMETABLE_TILES:],
            palette=bytes(self._palette[self._entry(entry)] for entry in range(PALETTE_SIZE)),
            sprites=bytes(self._sprites),
            control=self._control,
            mask=self._mask,
            scroll_x=(coarse_x << FINE_BITS) | self._fine_x,
            scroll_y=(coarse_y << FINE_BITS) | fine_y,
        )

    def finish_warming(self) -> None:
        """Ends the stretch after power-on in which four of the registers are ignored."""
        self._warming = False

    def begin_vertical_blank(self) -> None:
        """Sets the vertical blank flag, and raises the interrupt where the control register asks for it."""
        self._vertical_blank = True
        self._interrupt_due = self.interrupts

    def end_vertical_blank(self) -> None:
        """Clears the vertical blank flag, as the first line of the next picture does."""
        self._vertical_blank = False

    def take_interrupt(self) -> bool:
        """Answers whether an interrupt is due, and counts it as delivered."""
        due = self._interrupt_due
        self._interrupt_due = False
        return due

    def write(self, register: VideoRegister, value: int) -> None:
        """Takes one store to a register.

        Args:
            register: The register stored to.
            value: The byte stored.

        Raises:
            ReadOnlyMemoryError: If a store to the data register lands in the pattern tables.
        """
        if self._warming and register in WARMED_REGISTERS:
            return

        match register:
            case VideoRegister.CONTROL:
                self._write_control(value)
            case VideoRegister.MASK:
                self._mask = value
            case VideoRegister.STATUS:
                pass
            case VideoRegister.SPRITE_ADDRESS:
                self._sprite_address = value
            case VideoRegister.SPRITE_DATA:
                self._sprites[self._sprite_address] = value
                self._sprite_address = (self._sprite_address + 1) % SPRITE_MEMORY_SIZE
            case VideoRegister.SCROLL:
                self._write_scroll(value)
            case VideoRegister.ADDRESS:
                self._write_address(value)
            case VideoRegister.DATA:
                self._store(self._address, value)
                self._advance()

    def read(self, register: VideoRegister) -> int:
        """Answers one read of a register.

        Reading the status clears the vertical blank flag and resets the latch the scroll and
        address registers share. Reading the data register answers with the byte the previous
        read fetched, except in the palette, which answers at once.

        Args:
            register: The register read.

        Returns:
            int: The byte the register answers with.
        """
        match register:
            case VideoRegister.STATUS:
                return self._read_status()
            case VideoRegister.SPRITE_DATA:
                return self._sprites[self._sprite_address]
            case VideoRegister.DATA:
                return self._read_data()
            case _:
                return UNWRITTEN

    def transfer(self, page: Sequence[int]) -> None:
        """Copies a page of the console's memory into the sprite memory, from the sprite address onward.

        Args:
            page: The 256 bytes the transfer register names.
        """
        for offset, value in enumerate(page):
            self._sprites[(self._sprite_address + offset) % SPRITE_MEMORY_SIZE] = value

    def _write_control(self, value: int) -> None:
        raised = bool(value & CONTROL_INTERRUPT_FLAG) and not self.interrupts
        self._control = value
        self._pending = (self._pending & ~NAMETABLE_SELECT_MASK) | (
            (value & CONTROL_NAMETABLE_MASK) << NAMETABLE_SELECT_SHIFT
        )
        if raised and self._vertical_blank:
            self._interrupt_due = True

    def _write_scroll(self, value: int) -> None:
        if self._latched:
            self._pending = (
                (self._pending & ~(FINE_Y_MASK | COARSE_Y_MASK))
                | ((value & FINE_MASK) << FINE_Y_SHIFT)
                | ((value >> FINE_BITS) << COARSE_Y_SHIFT)
            )
        else:
            self._pending = (self._pending & ~COARSE_X_MASK) | (value >> FINE_BITS)
            self._fine_x = value & FINE_MASK

        self._latched = not self._latched

    def _write_address(self, value: int) -> None:
        if self._latched:
            self._pending = (self._pending & ~ADDRESS_LOW_MASK) | value
            self._address = self._pending
        else:
            self._pending = (self._pending & ADDRESS_LOW_MASK) | ((value & ADDRESS_HIGH_MASK) << ADDRESS_HIGH_SHIFT)

        self._latched = not self._latched

    def _read_status(self) -> int:
        status = STATUS_VERTICAL_BLANK_FLAG if self._vertical_blank else UNWRITTEN
        self._vertical_blank = False
        self._latched = False
        return status

    def _read_data(self) -> int:
        address = self._address % VIDEO_MEMORY_SIZE
        if address >= PALETTE_START:
            value = self._load(address)
            self._buffered = self._load(address - NAMETABLES_SPAN)
        else:
            value = self._buffered
            self._buffered = self._load(address)

        self._advance()
        return value

    def _advance(self) -> None:
        step = COLUMN_STEP if self._control & CONTROL_COLUMN_STEP_FLAG else ROW_STEP
        self._address = (self._address + step) & ADDRESS_MASK

    def _load(self, address: int) -> int:
        address %= VIDEO_MEMORY_SIZE
        if address < PATTERN_TABLES_END:
            return self._patterns[address]

        if address < PALETTE_START:
            return self._nametables[self._cell(address)]

        return self._palette[self._entry(address)]

    def _store(self, address: int, value: int) -> None:
        address %= VIDEO_MEMORY_SIZE
        if address < PATTERN_TABLES_END:
            raise ReadOnlyMemoryError(
                f"The program stored {value:#04x} at {address:#06x} of video memory, inside the cartridge's patterns"
            )

        if address < PALETTE_START:
            self._nametables[self._cell(address)] = value
        else:
            self._palette[self._entry(address)] = value & COLOR_MASK

    def _cell(self, address: int) -> int:
        """Where a nametable address lies in the two nametables the board holds."""
        table, offset = divmod((address - NAMETABLES_START) % NAMETABLES_SPAN, NAMETABLE_SIZE)
        return self._fold[table] * NAMETABLE_SIZE + offset

    @staticmethod
    def _entry(address: int) -> int:
        """Where a palette address lies, each sprite palette's first entry being the background's own."""
        entry = address % PALETTE_SIZE
        if entry >= SPRITE_PALETTES_OFFSET and entry % PALETTE_ENTRY_SIZE == 0:
            return entry - SPRITE_PALETTES_OFFSET

        return entry
