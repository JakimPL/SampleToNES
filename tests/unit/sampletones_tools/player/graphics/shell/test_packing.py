from dataclasses import dataclass
from typing import Final

import pytest

from sampletones_tools.player.graphics.shell.packing import (
    COPY_FLAG,
    END_MARK,
    LENGTH_SHIFT,
    LONGEST_TOKEN,
    WINDOW_SIZE,
    pack,
    unpack,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

VALUE: Final[int] = 0x20
OTHER: Final[int] = 0x41
PATTERN: Final[bytes] = bytes((0xE0, 0xE1, 0xE2))
DISTINCT: Final[bytes] = bytes(range(1, 201))


def literal_header(length: int) -> int:
    return length << LENGTH_SHIFT


def copy_header(length: int) -> int:
    return (length << LENGTH_SHIFT) | COPY_FLAG


class TestPackedData(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        data: bytes

    test_cases = (
        TestCase(data=b"", label="no data"),
        TestCase(data=bytes([VALUE]), label="one byte"),
        TestCase(data=bytes([VALUE]) * 3, label="a short run"),
        TestCase(data=bytes([VALUE]) * (2 * LONGEST_TOKEN + 5), label="a run longer than one header holds"),
        TestCase(data=DISTINCT + bytes([OTHER]), label="literals longer than one header holds"),
        TestCase(data=bytes([VALUE, VALUE, OTHER, OTHER, OTHER, VALUE]), label="a pair, a run and a single byte"),
        TestCase(
            data=PATTERN + DISTINCT + DISTINCT[:WINDOW_SIZE] + PATTERN, label="a repeat farther back than the window"
        ),
        TestCase(data=bytes(range(WINDOW_SIZE)) * 3, label="a stretch the window repeats whole"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_unpacking_gives_the_data_back(self, test_case: TestCase) -> None:
        assert unpack(pack(test_case.data)) == test_case.data

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_packed_data_closes_with_the_end_mark(self, test_case: TestCase) -> None:
        assert pack(test_case.data)[-1] == END_MARK

    def test_a_run_is_its_byte_and_a_copy_from_one_byte_back(self) -> None:
        packed = pack(bytes([VALUE]) * (LONGEST_TOKEN + 1))

        assert packed == bytes((literal_header(1), VALUE, copy_header(LONGEST_TOKEN), 0, END_MARK))

    def test_a_repeat_is_copied_from_where_the_window_holds_it(self) -> None:
        packed = pack(PATTERN * 2)

        assert packed == bytes((literal_header(len(PATTERN)), *PATTERN, copy_header(len(PATTERN)), 0, END_MARK))

    def test_a_copy_names_the_window_place_written_that_many_bytes_before(self) -> None:
        packed = pack(DISTINCT + PATTERN + PATTERN)
        start = len(DISTINCT)

        assert packed[-3:] == bytes((copy_header(len(PATTERN)), start % WINDOW_SIZE, END_MARK))

    def test_literals_longer_than_a_header_states_take_one_header_more(self) -> None:
        assert len(pack(DISTINCT)) == len(DISTINCT) + 2 + 1

    def test_data_without_its_end_mark_is_refused(self) -> None:
        with pytest.raises(ValueError, match="end mark"):
            unpack(pack(bytes([VALUE]) * 3)[:-1])
