from sampletones_player.rom.header import PATTERN_UNITS, PROGRAM_UNITS, rom_header
from sampletones_player.specification.memory import PROGRAM_SIZE
from sampletones_player.specification.rom import (
    BOARD_FLAGS_OFFSET,
    PATTERN_UNIT_SIZE,
    PATTERN_UNITS_OFFSET,
    PROGRAM_UNIT_SIZE,
    PROGRAM_UNITS_OFFSET,
    ROM_HEADER_SIZE,
    ROM_MAGIC,
    SYSTEM_FLAGS_OFFSET,
)
from sampletones_player.specification.screen import PATTERNS_SIZE
from tests.suite.base import BaseTestSuite


class TestTheCartridgeHeader(BaseTestSuite):
    def test_it_takes_the_size_of_an_ines_header(self) -> None:
        assert len(rom_header()) == ROM_HEADER_SIZE

    def test_it_opens_with_the_signature(self) -> None:
        assert rom_header().startswith(ROM_MAGIC)

    def test_it_states_the_whole_program_area(self) -> None:
        assert (
            rom_header()[PROGRAM_UNITS_OFFSET] * PROGRAM_UNIT_SIZE == PROGRAM_SIZE == PROGRAM_UNITS * PROGRAM_UNIT_SIZE
        )

    def test_it_states_both_pattern_tables(self) -> None:
        assert (
            rom_header()[PATTERN_UNITS_OFFSET] * PATTERN_UNIT_SIZE == PATTERNS_SIZE == PATTERN_UNITS * PATTERN_UNIT_SIZE
        )

    def test_it_names_the_plainest_board(self) -> None:
        header = rom_header()

        assert header[BOARD_FLAGS_OFFSET] == header[SYSTEM_FLAGS_OFFSET] == 0
        assert not any(header[SYSTEM_FLAGS_OFFSET + 1 :])
