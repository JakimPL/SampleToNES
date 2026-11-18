from dataclasses import dataclass
from typing import Final

import pytest

from sampletones_tools.player.graphics.shell.packing import END_MARK, LONGEST_RUN, pack, unpack
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

VALUE: Final[int] = 0x20
OTHER: Final[int] = 0x41


class TestPackedData(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        data: bytes

    test_cases = (
        TestCase(data=b"", label="no data"),
        TestCase(data=bytes([VALUE]), label="one byte"),
        TestCase(data=bytes([VALUE]) * 3, label="the shortest run"),
        TestCase(data=bytes([VALUE]) * (2 * LONGEST_RUN + 5), label="a run longer than one header holds"),
        TestCase(data=bytes(range(LONGEST_RUN)) * 2 + bytes([OTHER]), label="literals longer than one header holds"),
        TestCase(data=bytes([VALUE, VALUE, OTHER, OTHER, OTHER, VALUE]), label="a pair, a run and a single byte"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_unpacking_gives_the_data_back(self, test_case: TestCase) -> None:
        assert unpack(pack(test_case.data)) == test_case.data

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_packed_data_closes_with_the_end_mark(self, test_case: TestCase) -> None:
        assert pack(test_case.data)[-1] == END_MARK

    def test_a_run_is_a_header_and_its_byte(self) -> None:
        assert pack(bytes([VALUE]) * 3) == bytes((254, VALUE, END_MARK))

    def test_the_longest_run_takes_the_lowest_repeat_header(self) -> None:
        assert pack(bytes([VALUE]) * LONGEST_RUN) == bytes((129, VALUE, END_MARK))

    def test_a_pair_stays_among_the_literals(self) -> None:
        assert pack(bytes([VALUE, VALUE])) == bytes((1, VALUE, VALUE, END_MARK))

    def test_no_header_takes_the_end_mark_as_a_count(self) -> None:
        packed = pack(bytes(range(LONGEST_RUN)) * 3)

        assert packed.count(END_MARK) == 1 + bytes(range(LONGEST_RUN)).count(END_MARK) * 3

    def test_data_without_its_end_mark_is_refused(self) -> None:
        with pytest.raises(ValueError, match="end mark"):
            unpack(pack(bytes([VALUE]) * 3)[:-1])
