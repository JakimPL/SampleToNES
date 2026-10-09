from dataclasses import dataclass
from typing import Final, Tuple

import pytest

from sampletones_player.specification.nsf import (
    DUAL_REGION_FLAG,
    NTSC_PLAY_PERIOD_MICROSECONDS,
    NTSC_REGION,
    PAL_PLAY_PERIOD_MICROSECONDS,
    PAL_REGION_FLAG,
    PROGRAM_START,
)
from sampletones_shared.exceptions.validation import TruncatedDataError
from sampletones_tools.console.errors import NotAnNSFError
from sampletones_tools.console.header import NTSC_MACHINE, PAL_MACHINE, NSFHeader
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase
from tests.unit.sampletones_tools.console.files import INIT, LOADED_WHOLE, PLAY, NSFFile

BANKS: Final[Tuple[int, ...]] = (0, 1, 2, 3, 4, 5, 6, 7)
LOAD: Final[int] = PROGRAM_START + 0x0100


class TestReadingAHeader:
    def test_every_field_a_player_reads_comes_back(self) -> None:
        header = NSFHeader.read(NSFFile(load=LOAD, banks=BANKS, songs=3, first_song=2).data)

        assert header == NSFHeader(
            songs=3,
            first_song=2,
            load=LOAD,
            init=INIT,
            play=PLAY,
            ntsc_period=NTSC_PLAY_PERIOD_MICROSECONDS,
            banks=BANKS,
            pal_period=PAL_PLAY_PERIOD_MICROSECONDS,
            region=NTSC_REGION,
        )

    def test_the_first_song_is_handed_to_init_counted_from_zero(self) -> None:
        assert NSFHeader.read(NSFFile(songs=3, first_song=2).data).first_song_index == 1

    def test_a_header_naming_a_bank_is_banked(self) -> None:
        assert NSFHeader.read(NSFFile(banks=BANKS).data).banked
        assert not NSFHeader.read(NSFFile(banks=LOADED_WHOLE).data).banked

    def test_data_without_the_signature_is_refused(self) -> None:
        with pytest.raises(NotAnNSFError):
            NSFHeader.read(b"NESM\x00" + NSFFile().data[5:])

    def test_data_ending_inside_the_header_is_refused(self) -> None:
        with pytest.raises(TruncatedDataError):
            NSFHeader.read(NSFFile().data[:40])


class TestTheMachine(BaseTestSuite):
    """The init routine is told PAL for a file made for PAL alone, and NTSC for any other."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        region: int
        expected: int

        @property
        def label(self) -> str:
            return f"region-{self.region}"

    test_cases: Tuple[TestCase, ...] = (
        TestCase(region=NTSC_REGION, expected=NTSC_MACHINE),
        TestCase(region=PAL_REGION_FLAG, expected=PAL_MACHINE),
        TestCase(region=PAL_REGION_FLAG | DUAL_REGION_FLAG, expected=NTSC_MACHINE),
        TestCase(region=DUAL_REGION_FLAG, expected=NTSC_MACHINE),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_region_names_the_machine(self, test_case: TestCase) -> None:
        assert NSFHeader.read(NSFFile(region=test_case.region).data).machine == test_case.expected
