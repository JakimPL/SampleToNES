import struct
from dataclasses import dataclass
from typing import Final, Tuple

import pytest

from sampletones_core.constants.enums import GeneratorName
from sampletones_player.nsf.song import song_to_bytes
from sampletones_player.song import Song
from sampletones_player.specification.channels import CHANNEL_ORDER
from sampletones_player.specification.song import (
    LOOP_TICK_OFFSET,
    MAX_STREAM_OFFSET,
    NO_LOOP,
    SONG_HEADER_SIZE,
    STEP_FRACTION_OFFSET,
    STEP_WHOLE_OFFSET,
    STREAM_OFFSETS_OFFSET,
    TOTAL_TICKS_OFFSET,
    WORD_SIZE,
)
from sampletones_shared.exceptions import SongTooLargeError
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase
from tests.suite.player import (
    PLAYER_FULL_VOLUME,
    PLAYER_OCTAVE_UP_TIMER,
    PLAYER_REFERENCE_TIMER,
    PLAYER_SILENT_VOLUME,
    player_song,
    pulse_tick,
    resting_streams,
)

NTSC_FREQUENCY: Final[int] = 60
HALF_RATE_FREQUENCY: Final[int] = 30
PROGRAM_AREA_BYTES: Final[int] = 0x8000
UNBOUNDED_SPACE: Final[int] = MAX_STREAM_OFFSET * len(CHANNEL_ORDER)

SOUNDING: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_REFERENCE_TIMER)
RESTING: Final = pulse_tick(PLAYER_SILENT_VOLUME, 0, PLAYER_REFERENCE_TIMER)
OCTAVE_UP: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_OCTAVE_UP_TIMER)


def read_word(data: bytes, offset: int) -> int:
    return int(struct.unpack_from("<H", data, offset)[0])


def stream_offsets(data: bytes) -> Tuple[int, ...]:
    return tuple(read_word(data, STREAM_OFFSETS_OFFSET + WORD_SIZE * channel) for channel in range(len(CHANNEL_ORDER)))


def two_tick_song(nes_frequency: int) -> Song:
    return player_song(resting_streams((SOUNDING, RESTING)), nes_frequency, loop_tick=None)


class TestSongBytes:
    """The exact bytes a hand-built song serialises to.

    The layout is the contract the driver reads the song through, so the literal states it in
    full: a fifteen-byte header, then each channel's records back to back in channel order.
    """

    EXPECTED: Final[bytes] = (
        b"\x00\xff\x7f"
        b"\x02\x00"
        b"\xff\xff"
        b"\x0f\x00\x15\x00\x1b\x00\x21\x00"
        b"\x3f\x54\x01\x30\x54\x01"
        b"\x30\x54\x01\x30\x54\x01"
        b"\x80\x54\x01\x80\x54\x01"
        b"\x30\x0a\x30\x0a"
    )

    def test_the_song_serialises_to_the_expected_bytes(self) -> None:
        assert song_to_bytes(two_tick_song(HALF_RATE_FREQUENCY), PROGRAM_AREA_BYTES) == self.EXPECTED

    def test_the_streams_begin_where_the_header_ends(self) -> None:
        assert stream_offsets(self.EXPECTED)[0] == SONG_HEADER_SIZE


class TestSongHeader(BaseTestSuite):
    """Each header field carries the value its offset is read for."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: int
        name: str
        nes_frequency: int

        @property
        def label(self) -> str:
            return self.name

    test_cases: Tuple[TestCase, ...] = (
        TestCase(name="60hz-whole", nes_frequency=NTSC_FREQUENCY, expected=0),
        TestCase(name="30hz-whole", nes_frequency=HALF_RATE_FREQUENCY, expected=0),
        TestCase(name="120hz-whole", nes_frequency=120, expected=1),
        TestCase(name="300hz-whole", nes_frequency=300, expected=4),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_step_reaches_the_header_as_the_driver_holds_it(self, test_case: TestCase) -> None:
        song = two_tick_song(test_case.nes_frequency)
        data = song_to_bytes(song, PROGRAM_AREA_BYTES)
        step = song.schedule.fixed_point_step
        assert data[STEP_WHOLE_OFFSET] == test_case.expected
        assert data[STEP_WHOLE_OFFSET] == step.whole
        assert read_word(data, STEP_FRACTION_OFFSET) == step.fraction

    def test_the_header_states_the_songs_length(self) -> None:
        song = player_song(resting_streams((SOUNDING, OCTAVE_UP, RESTING)), NTSC_FREQUENCY, loop_tick=None)
        data = song_to_bytes(song, PROGRAM_AREA_BYTES)
        assert read_word(data, TOTAL_TICKS_OFFSET) == song.ticks

    def test_a_song_that_stops_states_no_loop(self) -> None:
        data = song_to_bytes(two_tick_song(NTSC_FREQUENCY), PROGRAM_AREA_BYTES)
        assert read_word(data, LOOP_TICK_OFFSET) == NO_LOOP

    def test_a_song_that_repeats_states_its_loop_tick(self) -> None:
        song = player_song(resting_streams((SOUNDING, RESTING)), NTSC_FREQUENCY, loop_tick=1)
        data = song_to_bytes(song, PROGRAM_AREA_BYTES)
        assert read_word(data, LOOP_TICK_OFFSET) == 1


class TestStreamOffsets:
    """Every channel's stream is found where the header says it is."""

    def test_the_first_stream_begins_past_the_header(self) -> None:
        data = song_to_bytes(two_tick_song(NTSC_FREQUENCY), PROGRAM_AREA_BYTES)
        assert stream_offsets(data)[0] == SONG_HEADER_SIZE

    def test_the_offsets_ascend_in_channel_order(self) -> None:
        data = song_to_bytes(two_tick_song(NTSC_FREQUENCY), PROGRAM_AREA_BYTES)
        offsets = stream_offsets(data)
        assert list(offsets) == sorted(offsets)

    def test_each_offset_lands_on_that_channels_first_record(self) -> None:
        song = two_tick_song(NTSC_FREQUENCY)
        data = song_to_bytes(song, PROGRAM_AREA_BYTES)
        for offset, stream in zip(stream_offsets(data), song.streams.padded):
            assert tuple(data[offset : offset + len(stream[0].values)]) == stream[0].values

    def test_the_streams_fill_the_song_to_its_last_byte(self) -> None:
        song = two_tick_song(NTSC_FREQUENCY)
        data = song_to_bytes(song, PROGRAM_AREA_BYTES)
        records = sum(len(registers.values) for stream in song.streams.padded for registers in stream)
        assert len(data) == SONG_HEADER_SIZE + records

    def test_a_shorter_channel_is_written_to_the_songs_length(self) -> None:
        song = player_song(resting_streams((SOUNDING, OCTAVE_UP, RESTING)), NTSC_FREQUENCY, loop_tick=None)
        data = song_to_bytes(song, PROGRAM_AREA_BYTES)
        offsets = stream_offsets(data)
        noise_bytes = data[offsets[3] :]
        assert noise_bytes == bytes(song.streams.noise[0].values) * song.ticks


class TestSongTooLarge:
    """A song that outgrows what the header or the console can hold names the overflow."""

    def test_a_song_past_the_available_space_raises(self) -> None:
        song = two_tick_song(NTSC_FREQUENCY)
        data = song_to_bytes(song, PROGRAM_AREA_BYTES)
        with pytest.raises(SongTooLargeError):
            song_to_bytes(song, len(data) - 1)

    def test_a_song_filling_the_available_space_exactly_is_written(self) -> None:
        song = two_tick_song(NTSC_FREQUENCY)
        data = song_to_bytes(song, PROGRAM_AREA_BYTES)
        assert song_to_bytes(song, len(data)) == data

    def test_a_song_reaching_past_the_offset_field_raises(self) -> None:
        ticks = MAX_STREAM_OFFSET // len(SOUNDING.values) + 1
        song = player_song(resting_streams((SOUNDING,) * ticks), NTSC_FREQUENCY, loop_tick=None)
        with pytest.raises(SongTooLargeError, match=GeneratorName.PULSE2.value):
            song_to_bytes(song, UNBOUNDED_SPACE)
