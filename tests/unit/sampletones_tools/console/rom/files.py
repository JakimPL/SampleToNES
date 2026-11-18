from dataclasses import dataclass, field
from typing import Callable, Dict, Final, Self, Tuple

from sampletones_core.formats.binary import BinaryWriter
from sampletones_player.specification.memory import (
    IRQ_VECTOR,
    NMI_VECTOR,
    RESET_VECTOR,
)
from sampletones_player.specification.nsf import PROGRAM_SIZE, PROGRAM_START
from sampletones_player.specification.rom import (
    MAPPER_HIGH_NIBBLE_MASK,
    MAPPER_NIBBLE_SHIFT,
    NROM_MAPPER,
    PADDING_SIZE,
    PATTERN_UNIT_SIZE,
    PROGRAM_UNIT_SIZE,
    ROM_MAGIC,
)
from sampletones_tools.console.rom.registers import (
    CONTROL_INTERRUPT_FLAG,
    VideoRegister,
)
from tests.unit.sampletones_tools.console.files import (
    JUMP,
    LOAD_ABSOLUTE,
    LOAD_IMMEDIATE,
    STORE_ACCUMULATOR,
    absolute,
)

Code = Tuple[int, ...]

RESET: Final[int] = PROGRAM_START
INTERRUPT: Final[int] = PROGRAM_START + 0x0100
UNUSED_INTERRUPT: Final[int] = PROGRAM_START + 0x0200
WHOLE_PROGRAM_UNITS: Final[int] = PROGRAM_SIZE // PROGRAM_UNIT_SIZE
ONE_PATTERN_UNIT: Final[int] = 1
HORIZONTAL_BOARD: Final[int] = 0x00
BYTE_MASK: Final[int] = 0xFF
BLANK_PATTERNS: Final[bytes] = bytes(PATTERN_UNIT_SIZE)

LOAD_INDEX: Final[int] = 0xA2
LOAD_SECOND_INDEX: Final[int] = 0xA0
LOAD_ZERO_PAGE: Final[int] = 0xA5
INCREMENT_ZERO_PAGE: Final[int] = 0xE6
DECREMENT_INDEX: Final[int] = 0xCA
DECREMENT_SECOND_INDEX: Final[int] = 0x88
TEST_BITS: Final[int] = 0x2C
BRANCH_PLUS: Final[int] = 0x10
BRANCH_NOT_EQUAL: Final[int] = 0xD0
AND_IMMEDIATE: Final[int] = 0x29
NO_OPERATION: Final[int] = 0xEA
RETURN_FROM_INTERRUPT: Final[int] = 0x40

LOAD_IMMEDIATE_CYCLES: Final[int] = 2
STORE_ABSOLUTE_CYCLES: Final[int] = 4
JUMP_CYCLES: Final[int] = 3
RETURN_FROM_INTERRUPT_CYCLES: Final[int] = 6
INNER_SPIN_CYCLES: Final[int] = 256 * 5 - 1
OUTER_SPIN_CYCLES: Final[int] = INNER_SPIN_CYCLES + 7


def branch_back(length: int) -> int:
    """The operand of a branch returning over the ``length`` bytes that end with the branch itself."""
    return 0x100 - length


def joined(*parts: Code) -> Code:
    """Several runs of code as the one run they assemble to."""
    return tuple(byte for part in parts for byte in part)


def load(value: int) -> Code:
    return (LOAD_IMMEDIATE, value)


def store(address: int) -> Code:
    return (STORE_ACCUMULATOR, *absolute(address))


def fetch(address: int) -> Code:
    return (LOAD_ABSOLUTE, *absolute(address))


def put(address: int, value: int) -> Code:
    """Stores ``value`` at ``address`` through the accumulator."""
    return joined(load(value), store(address))


def spin(address: int) -> Code:
    """The idle loop a program rests in: a jump to itself, assembled for the address it stands at."""
    return (JUMP, *absolute(address))


def spun_out(turns: int) -> Code:
    """A loop that stores nothing and falls through a cycle past ``turns`` times `OUTER_SPIN_CYCLES`."""
    return (
        LOAD_SECOND_INDEX,
        turns,
        LOAD_INDEX,
        0x00,
        DECREMENT_INDEX,
        BRANCH_NOT_EQUAL,
        branch_back(3),
        DECREMENT_SECOND_INDEX,
        BRANCH_NOT_EQUAL,
        branch_back(8),
    )


AWAIT_VERTICAL_BLANK: Final[Code] = (
    TEST_BITS,
    *absolute(VideoRegister.STATUS.address),
    BRANCH_PLUS,
    branch_back(5),
)
ENABLE_INTERRUPT: Final[Code] = put(VideoRegister.CONTROL.address, CONTROL_INTERRUPT_FLAG)
NOTHING: Final[Code] = ()


def booting(
    *,
    before: Code = NOTHING,
    setup: Code = NOTHING,
    rest: Callable[[int], Code] = spin,
) -> Code:
    """A reset routine: it waits out two vertical blanks, sets up, switches the frame interrupt on and rests.

    Args:
        before: What the routine does ahead of the waits, inside the picture processor's warm-up.
        setup: What the routine does between the waits and switching the interrupt on.
        rest: The idle loop the routine ends in, built for the address it lands at.

    Returns:
        Code: The routine, assembled for `RESET`.
    """
    body = joined(before, AWAIT_VERTICAL_BLANK, AWAIT_VERTICAL_BLANK, setup, ENABLE_INTERRUPT)
    return joined(body, rest(RESET + len(body)))


@dataclass(frozen=True)
class ROMFile:
    """A small cartridge image written for a case: an iNES header, a program placed at its addresses, and patterns.

    Attributes:
        program_units: How many 16 KB units of program the header names and the image holds.
        pattern_units: How many 8 KB units of patterns the header names.
        board: The header's board byte, less the mapper's low half.
        mapper: The mapper the header names.
        program: The program's bytes, keyed by their offset within the program image.
        patterns: The pattern tables the image holds behind its program.
    """

    program_units: int = WHOLE_PROGRAM_UNITS
    pattern_units: int = ONE_PATTERN_UNIT
    board: int = HORIZONTAL_BOARD
    mapper: int = NROM_MAPPER
    program: Dict[int, Code] = field(default_factory=dict)
    patterns: bytes = BLANK_PATTERNS

    @classmethod
    def running(cls, reset: Code, interrupt: Code) -> Self:
        """An image whose reset routine stands at `RESET` and whose frame interrupt routine at `INTERRUPT`."""
        return cls(program={RESET - PROGRAM_START: reset, INTERRUPT - PROGRAM_START: interrupt})

    @property
    def image(self) -> bytes:
        """The program image: each part at its offset, zeros between, and the three vectors in its last bytes."""
        size = self.program_units * PROGRAM_UNIT_SIZE
        image = bytearray(size)
        for offset, code in self.program.items():
            image[offset : offset + len(code)] = bytes(code)

        last_unit = PROGRAM_START + PROGRAM_SIZE - size
        for vector, address in (
            (NMI_VECTOR, INTERRUPT),
            (RESET_VECTOR, RESET),
            (IRQ_VECTOR, UNUSED_INTERRUPT),
        ):
            image[vector - last_unit : vector - last_unit + 2] = bytes(absolute(address))

        return bytes(image)

    @property
    def data(self) -> bytes:
        """The whole file, header first."""
        writer = BinaryWriter()
        writer.write_bytes(ROM_MAGIC)
        writer.write_uint8(self.program_units)
        writer.write_uint8(self.pattern_units)
        writer.write_uint8(self.board | ((self.mapper << MAPPER_NIBBLE_SHIFT) & BYTE_MASK))
        writer.write_uint8(self.mapper & MAPPER_HIGH_NIBBLE_MASK)
        writer.write_bytes(bytes(PADDING_SIZE))
        writer.write_bytes(self.image)
        writer.write_bytes(self.patterns)
        return writer.data
