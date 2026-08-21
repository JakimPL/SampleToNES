import struct
from dataclasses import dataclass
from fractions import Fraction
from typing import Final, Tuple

import pytest

from sampletones_player.driver.addresses import DriverAddresses
from sampletones_player.nsf.header import header_to_bytes
from sampletones_player.nsf.information import NSFInformation
from sampletones_player.specification.clock import (
    MICROSECONDS_PER_SECOND,
    NTSC_FRAME_RATE,
)
from sampletones_player.specification.nsf import (
    ARTIST_OFFSET,
    BANKSWITCH_OFFSET,
    BANKSWITCH_SIZE,
    COPYRIGHT_OFFSET,
    EXPANSION_OFFSET,
    FIRST_SONG,
    FIRST_SONG_OFFSET,
    HEADER_SIZE,
    INIT_ADDRESS_OFFSET,
    LOAD_ADDRESS_OFFSET,
    MAGIC_OFFSET,
    NO_EXPANSION_CHIPS,
    NO_NSF2_FEATURES,
    NSF2_FEATURES_OFFSET,
    NSF2_LENGTH_OFFSET,
    NSF2_LENGTH_SIZE,
    NSF_MAGIC,
    NSF_VERSION,
    NTSC_PERIOD_OFFSET,
    NTSC_PLAY_PERIOD_MICROSECONDS,
    NTSC_REGION,
    PAL_PERIOD_OFFSET,
    PAL_PLAY_PERIOD_MICROSECONDS,
    PLAY_ADDRESS_OFFSET,
    REGION_OFFSET,
    SONG_COUNT,
    SONG_COUNT_OFFSET,
    STRING_FIELD_SIZE,
    TITLE_OFFSET,
    VERSION_OFFSET,
)
from sampletones_shared.application import SAMPLETONES_COPYRIGHT
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase

SONG_ADDRESS: Final[int] = 0x8153
TITLE: Final[str] = "Amen"
ARTIST: Final[str] = "Jakim"
ADDRESSES: Final[DriverAddresses] = DriverAddresses(song=SONG_ADDRESS)
INFORMATION: Final[NSFInformation] = NSFInformation(title=TITLE, artist=ARTIST)
RATE_TOLERANCE: Final[Fraction] = Fraction(1, 10_000)


def header() -> bytes:
    return header_to_bytes(INFORMATION, ADDRESSES)


def read_word(data: bytes, offset: int) -> int:
    return int(struct.unpack_from("<H", data, offset)[0])


def read_string(data: bytes, offset: int) -> bytes:
    return data[offset : offset + STRING_FIELD_SIZE]


class TestHeaderBytes:
    """The exact bytes an NSF header serialises to.

    The layout is what every console player reads a file through, so the literal states it in
    full: the identity, the three addresses, the three text fields, and the playback fields
    behind them.
    """

    EXPECTED: Final[bytes] = (
        NSF_MAGIC
        + b"\x01\x01\x01"
        + b"\x00\x80\x00\x80\x03\x80"
        + TITLE.encode("utf-8").ljust(STRING_FIELD_SIZE, b"\x00")
        + ARTIST.encode("utf-8").ljust(STRING_FIELD_SIZE, b"\x00")
        + SAMPLETONES_COPYRIGHT.encode("utf-8").ljust(STRING_FIELD_SIZE, b"\x00")
        + b"\xff\x40"
        + bytes(BANKSWITCH_SIZE)
        + b"\x20\x4e"
        + b"\x00\x00\x00"
        + bytes(NSF2_LENGTH_SIZE)
    )

    def test_the_header_serialises_to_the_expected_bytes(self) -> None:
        assert header() == self.EXPECTED

    def test_the_header_fills_the_program_area_it_precedes(self) -> None:
        assert len(header()) == HEADER_SIZE


class TestHeaderIdentity:
    """What names the file an NSF, and the one tune it carries."""

    def test_the_header_leads_with_the_magic(self) -> None:
        assert header()[MAGIC_OFFSET : MAGIC_OFFSET + len(NSF_MAGIC)] == NSF_MAGIC

    def test_the_header_states_its_version(self) -> None:
        assert header()[VERSION_OFFSET] == NSF_VERSION

    def test_the_file_carries_one_tune(self) -> None:
        assert header()[SONG_COUNT_OFFSET] == SONG_COUNT

    def test_the_tune_it_opens_on_is_the_one_it_carries(self) -> None:
        assert header()[FIRST_SONG_OFFSET] == FIRST_SONG == SONG_COUNT


class TestHeaderRoutines:
    """The addresses a console loads the image at and drives it through."""

    def test_the_load_address_is_where_the_driver_loads(self) -> None:
        assert read_word(header(), LOAD_ADDRESS_OFFSET) == ADDRESSES.load

    def test_the_init_address_is_the_drivers_own(self) -> None:
        assert read_word(header(), INIT_ADDRESS_OFFSET) == ADDRESSES.init

    def test_the_play_address_is_the_drivers_own(self) -> None:
        assert read_word(header(), PLAY_ADDRESS_OFFSET) == ADDRESSES.play


class TestHeaderStrings(BaseTestSuite):
    """The three text fields, each written into a fixed field and padded out with NULs."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        offset: int
        expected: str

        @property
        def label(self) -> str:
            return self.expected

    test_cases = (
        TestCase(offset=TITLE_OFFSET, expected=TITLE),
        TestCase(offset=ARTIST_OFFSET, expected=ARTIST),
        TestCase(offset=COPYRIGHT_OFFSET, expected=SAMPLETONES_COPYRIGHT),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_field_carries_its_text(self, test_case: TestCase) -> None:
        field = read_string(header(), test_case.offset)
        assert field == test_case.expected.encode("utf-8").ljust(STRING_FIELD_SIZE, b"\x00")

    def test_text_longer_than_the_field_is_written_as_much_as_fits(self) -> None:
        overlong = "A" * (STRING_FIELD_SIZE * 2)
        data = header_to_bytes(NSFInformation(title=overlong, artist=ARTIST), ADDRESSES)
        assert read_string(data, TITLE_OFFSET) == overlong.encode("utf-8")[:STRING_FIELD_SIZE]

    def test_the_fields_stand_back_to_back(self) -> None:
        assert (ARTIST_OFFSET - TITLE_OFFSET, COPYRIGHT_OFFSET - ARTIST_OFFSET) == (
            STRING_FIELD_SIZE,
            STRING_FIELD_SIZE,
        )


class TestHeaderPlayback:
    """The rate the console drives the file at, and the hardware it asks for."""

    def test_the_ntsc_period_is_the_one_the_specification_names(self) -> None:
        assert read_word(header(), NTSC_PERIOD_OFFSET) == NTSC_PLAY_PERIOD_MICROSECONDS

    def test_the_ntsc_period_asks_for_the_rate_the_schedule_counts_in(self) -> None:
        """A player reading the field and one driving from the frame run a stream at one speed."""
        requested = Fraction(MICROSECONDS_PER_SECOND, read_word(header(), NTSC_PERIOD_OFFSET))
        assert abs(requested - NTSC_FRAME_RATE) / NTSC_FRAME_RATE < RATE_TOLERANCE

    def test_the_pal_period_states_the_fiftieth_of_a_second(self) -> None:
        assert read_word(header(), PAL_PERIOD_OFFSET) == PAL_PLAY_PERIOD_MICROSECONDS

    def test_the_image_loads_whole(self) -> None:
        assert header()[BANKSWITCH_OFFSET : BANKSWITCH_OFFSET + BANKSWITCH_SIZE] == bytes(BANKSWITCH_SIZE)

    def test_the_tune_is_ntsc(self) -> None:
        assert header()[REGION_OFFSET] == NTSC_REGION

    def test_the_tune_plays_on_the_2a03_alone(self) -> None:
        assert header()[EXPANSION_OFFSET] == NO_EXPANSION_CHIPS

    def test_the_header_states_the_first_nsf_version(self) -> None:
        trailing: Tuple[int, ...] = tuple(header()[NSF2_LENGTH_OFFSET : NSF2_LENGTH_OFFSET + NSF2_LENGTH_SIZE])
        assert header()[NSF2_FEATURES_OFFSET] == NO_NSF2_FEATURES
        assert trailing == (0,) * NSF2_LENGTH_SIZE
