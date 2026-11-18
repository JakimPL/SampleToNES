from dataclasses import dataclass
from typing import Final, Tuple

import pytest
from py65.memory import ObservableMemory

from sampletones_player.specification.nsf import PROGRAM_SIZE, PROGRAM_START
from sampletones_player.specification.rom import (
    ALTERNATIVE_LAYOUT_FLAG,
    PATTERN_UNIT_SIZE,
    PROGRAM_UNIT_SIZE,
    ROM_HEADER_SIZE,
    TRAINER_FLAG,
    VERTICAL_MIRRORING_FLAG,
)
from sampletones_shared.exceptions.validation import TruncatedDataError
from sampletones_tools.console.rom.cartridge import ROMCartridge
from sampletones_tools.console.rom.errors import (
    ReadOnlyMemoryError,
    UnsupportedCartridgeError,
)
from sampletones_tools.console.rom.header import Mirroring, ROMHeader
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.unit.sampletones_tools.console.rom.files import ROMFile

MARKS: Final[Tuple[int, int]] = (0x11, 0x22)
LAST_PROGRAM_OFFSET: Final[int] = PROGRAM_SIZE - 0x10
HALF_PROGRAM_UNITS: Final[int] = 1
SECOND_HALF: Final[int] = PROGRAM_START + PROGRAM_UNIT_SIZE
PATTERNS: Final[bytes] = bytes(index % 251 for index in range(PATTERN_UNIT_SIZE))


def _cartridge(file: ROMFile) -> ROMCartridge:
    data = file.data
    return ROMCartridge(ROMHeader.read(data), data[ROM_HEADER_SIZE:])


class TestMounting:
    def test_a_whole_program_fills_the_program_area(self) -> None:
        file = ROMFile(program={0: (MARKS[0],), LAST_PROGRAM_OFFSET: (MARKS[1],)})
        memory = ObservableMemory()

        _cartridge(file).mount(memory)

        assert (memory[PROGRAM_START], memory[PROGRAM_START + LAST_PROGRAM_OFFSET]) == MARKS

    def test_a_half_program_answers_in_both_halves(self) -> None:
        file = ROMFile(program_units=HALF_PROGRAM_UNITS, program={0: (MARKS[0],)})
        memory = ObservableMemory()

        _cartridge(file).mount(memory)

        assert (memory[PROGRAM_START], memory[SECOND_HALF]) == (MARKS[0], MARKS[0])

    def test_a_store_into_the_program_is_refused(self) -> None:
        memory = ObservableMemory()
        _cartridge(ROMFile()).mount(memory)

        with pytest.raises(ReadOnlyMemoryError):
            memory[PROGRAM_START] = MARKS[0]


class TestWhatACartridgeHolds:
    def test_the_patterns_are_the_bytes_behind_the_program(self) -> None:
        assert _cartridge(ROMFile(patterns=PATTERNS)).patterns == PATTERNS

    def test_the_board_states_the_mirroring(self) -> None:
        assert _cartridge(ROMFile(board=VERTICAL_MIRRORING_FLAG)).mirroring is Mirroring.VERTICAL

    def test_an_image_ending_inside_its_patterns_is_refused(self) -> None:
        data = ROMFile().data

        with pytest.raises(TruncatedDataError):
            ROMCartridge(ROMHeader.read(data), data[ROM_HEADER_SIZE:-1])


class TestOtherBoards(BaseTestSuite):
    """The console models NROM alone: a fixed program of one or two units over 8 KB of pattern ROM."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        file: ROMFile

    test_cases: Tuple[TestCase, ...] = (
        TestCase(label="another-mapper", file=ROMFile(mapper=2)),
        TestCase(label="a-trainer", file=ROMFile(board=TRAINER_FLAG)),
        TestCase(label="an-alternative-layout", file=ROMFile(board=ALTERNATIVE_LAYOUT_FLAG)),
        TestCase(label="pattern-ram", file=ROMFile(pattern_units=0)),
        TestCase(label="a-switched-program", file=ROMFile(program_units=4)),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_image_is_refused(self, test_case: TestCase) -> None:
        with pytest.raises(UnsupportedCartridgeError):
            _cartridge(test_case.file)
