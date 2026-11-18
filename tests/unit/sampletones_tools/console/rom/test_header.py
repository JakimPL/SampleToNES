from dataclasses import dataclass
from typing import Tuple

import pytest

from sampletones_player.specification.rom import (
    ALTERNATIVE_LAYOUT_FLAG,
    BATTERY_FLAG,
    PATTERN_UNIT_SIZE,
    PROGRAM_UNIT_SIZE,
    ROM_HEADER_SIZE,
    TRAINER_FLAG,
    VERTICAL_MIRRORING_FLAG,
)
from sampletones_shared.exceptions.validation import TruncatedDataError
from sampletones_tools.console.rom.errors import NotAROMError
from sampletones_tools.console.rom.header import Mirroring, ROMHeader
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase, BaseRegularTestCase
from tests.unit.sampletones_tools.console.rom.files import HORIZONTAL_BOARD, ROMFile


class TestReadingAHeader:
    def test_every_field_a_console_reads_comes_back(self) -> None:
        header = ROMHeader.read(ROMFile(program_units=1, pattern_units=1, board=BATTERY_FLAG).data)

        assert header == ROMHeader(program_units=1, pattern_units=1, board=BATTERY_FLAG, system=0)

    def test_the_units_state_the_bytes_the_image_holds(self) -> None:
        header = ROMHeader.read(ROMFile(program_units=2, pattern_units=1).data)

        assert (header.program_size, header.pattern_size) == (2 * PROGRAM_UNIT_SIZE, PATTERN_UNIT_SIZE)

    def test_the_header_takes_the_sixteen_bytes_the_format_gives_it(self) -> None:
        """The iNES header is 16 bytes long, which is where every reader looks for the program."""
        file = ROMFile()

        assert ROM_HEADER_SIZE == 16
        assert file.data[ROM_HEADER_SIZE:] == file.image + file.patterns

    def test_data_without_the_signature_is_refused(self) -> None:
        with pytest.raises(NotAROMError):
            ROMHeader.read(b"NES\x00" + ROMFile().data[4:])

    def test_data_ending_inside_the_header_is_refused(self) -> None:
        with pytest.raises(TruncatedDataError):
            ROMHeader.read(ROMFile().data[: ROM_HEADER_SIZE - 1])


class TestTheMapper(BaseTestSuite):
    """The mapper's number is read from two bytes, its low half from the board byte and its high half beside it."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: int

        @property
        def label(self) -> str:
            return f"mapper-{self.expected}"

    test_cases: Tuple[TestCase, ...] = (
        TestCase(expected=0),
        TestCase(expected=2),
        TestCase(expected=31),
        TestCase(expected=206),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_both_halves_make_the_number(self, test_case: TestCase) -> None:
        assert ROMHeader.read(ROMFile(mapper=test_case.expected).data).mapper == test_case.expected


class TestTheBoard(BaseTestSuite):
    """Each flag of the board byte states one fact about the cartridge's wiring."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        board: int
        expected: Tuple[Mirroring, bool, bool, bool]

    test_cases: Tuple[TestCase, ...] = (
        TestCase(
            label="plain",
            board=HORIZONTAL_BOARD,
            expected=(Mirroring.HORIZONTAL, False, False, False),
        ),
        TestCase(
            label="vertical",
            board=VERTICAL_MIRRORING_FLAG,
            expected=(Mirroring.VERTICAL, False, False, False),
        ),
        TestCase(
            label="battery",
            board=BATTERY_FLAG,
            expected=(Mirroring.HORIZONTAL, True, False, False),
        ),
        TestCase(
            label="trainer",
            board=TRAINER_FLAG,
            expected=(Mirroring.HORIZONTAL, False, True, False),
        ),
        TestCase(
            label="alternative-layout",
            board=ALTERNATIVE_LAYOUT_FLAG,
            expected=(Mirroring.HORIZONTAL, False, False, True),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_flag_states_its_fact(self, test_case: TestCase) -> None:
        header = ROMHeader.read(ROMFile(board=test_case.board).data)

        assert (header.mirroring, header.battery, header.trainer, header.alternative_layout) == test_case.expected
