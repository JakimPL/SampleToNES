import struct
from dataclasses import dataclass
from typing import Final, Tuple

import pytest

from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.nsf.layout import NAME_SEPARATOR, SongLayout
from sampletones_player.nsf.song import song_to_bytes
from sampletones_player.song import Song
from sampletones_player.specification.binary import WORD_SIZE
from sampletones_player.specification.compression import PLANE_COUNT
from sampletones_player.specification.song import (
    LOOP_ENTRIES_OFFSET,
    LOOP_TICK_OFFSET,
    MAX_BLOCK_OFFSET,
    NO_LOOP,
    PHRASE_TABLE_OFFSET,
    SONG_HEADER_SIZE,
    STEP_FRACTION_OFFSET,
    STEP_WHOLE_OFFSET,
    STREAM_OFFSETS_OFFSET,
    TIMER_TABLE_OFFSET,
    TOTAL_TICKS_OFFSET,
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
    spelled_song,
)

NTSC_FREQUENCY: Final[int] = 60
HALF_RATE_FREQUENCY: Final[int] = 30
PROGRAM_AREA_BYTES: Final[int] = 0x8000
LOOP_TICK: Final[int] = 2

SOUNDING: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_REFERENCE_TIMER)
RESTING: Final = pulse_tick(PLAYER_SILENT_VOLUME, 0, PLAYER_REFERENCE_TIMER)
OCTAVE_UP: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_OCTAVE_UP_TIMER)


def read_word(data: bytes, offset: int) -> int:
    return int(struct.unpack_from("<H", data, offset)[0])


def read_words(data: bytes, offset: int, count: int) -> Tuple[int, ...]:
    return tuple(read_word(data, offset + WORD_SIZE * field) for field in range(count))


def stream_offsets(data: bytes) -> Tuple[int, ...]:
    return read_words(data, STREAM_OFFSETS_OFFSET, PLANE_COUNT)


def loop_entries(data: bytes) -> Tuple[int, ...]:
    return read_words(data, LOOP_ENTRIES_OFFSET, PLANE_COUNT)


def two_tick_song(nes_frequency: int) -> Song:
    return player_song(resting_streams((SOUNDING, RESTING)), nes_frequency, loop_tick=None)


def repeating_song() -> Song:
    return player_song(
        resting_streams((SOUNDING, OCTAVE_UP, RESTING, SOUNDING)),
        NTSC_FREQUENCY,
        loop_tick=LOOP_TICK,
    )


class TestSongBytes:
    """The exact bytes a hand-built song serializes to.

    The layout is the contract the driver reads the song through, so the literal states it in
    full: the header, the timer every pitch sounds at, the dictionary the tokens name, and one
    token stream per plane. The timer table is named rather than transcribed, since it is the
    tuning's own table and the block carries whatever that table holds.
    """

    EXPECTED_HEADER: Final[bytes] = (
        b"\x00"
        b"\xca\x7f"
        b"\x02\x00"
        b"\xff\xff"
        b"\x37\x00"
        b"\x07\x01"
        b"\x08\x01\x0b\x01\x0e\x01"
        b"\x11\x01\x14\x01\x17\x01"
        b"\x1a\x01\x1d\x01\x20\x01"
        b"\x23\x01\x26\x01"
        b"\x08\x01\x0b\x01\x0e\x01"
        b"\x11\x01\x14\x01\x17\x01"
        b"\x1a\x01\x1d\x01\x20\x01"
        b"\x23\x01\x26\x01"
    )

    EXPECTED_STREAMS: Final[bytes] = (
        b"\x00"
        b"\x41\x3f\x30"
        b"\x40\x21\x00"
        b"\x40\x00\x00"
        b"\x40\x30\x00"
        b"\x40\x21\x00"
        b"\x40\x00\x00"
        b"\x40\x80\x00"
        b"\x40\x21\x00"
        b"\x40\x00\x00"
        b"\x40\x30\x00"
        b"\x40\x0a\x00"
    )

    def test_the_song_serializes_to_the_expected_bytes(self) -> None:
        song = two_tick_song(HALF_RATE_FREQUENCY)
        expected = self.EXPECTED_HEADER + song.pitches.data + self.EXPECTED_STREAMS
        assert song_to_bytes(song, PROGRAM_AREA_BYTES) == expected

    def test_the_header_runs_to_the_length_the_offsets_are_read_at(self) -> None:
        assert len(self.EXPECTED_HEADER) == SONG_HEADER_SIZE


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
        data = song_to_bytes(repeating_song(), PROGRAM_AREA_BYTES)
        assert read_word(data, LOOP_TICK_OFFSET) == LOOP_TICK


class TestTimerTable:
    """The timer every pitch sounds at, where the header says it lies."""

    def test_the_table_begins_where_the_header_states(self) -> None:
        song = two_tick_song(NTSC_FREQUENCY)
        data = song_to_bytes(song, PROGRAM_AREA_BYTES)
        offset = read_word(data, TIMER_TABLE_OFFSET)
        assert data[offset : offset + len(song.pitches.data)] == song.pitches.data

    def test_the_table_follows_the_header(self) -> None:
        data = song_to_bytes(two_tick_song(NTSC_FREQUENCY), PROGRAM_AREA_BYTES)
        assert read_word(data, TIMER_TABLE_OFFSET) == SONG_HEADER_SIZE


class TestPhraseTable:
    """The dictionary the tokens name, counted and then reached through its own offsets."""

    def test_the_table_states_how_many_phrases_it_holds(self) -> None:
        song = repeating_song()
        data = song_to_bytes(song, PROGRAM_AREA_BYTES)
        assert data[read_word(data, PHRASE_TABLE_OFFSET)] == len(song.planes.phrases)

    def test_each_entry_reaches_that_phrases_length_and_body(self) -> None:
        song = spelled_phrase_song()
        data = song_to_bytes(song, PROGRAM_AREA_BYTES)
        layout = SongLayout.of(song)
        for phrase, offset in zip(song.planes.phrases.phrases, layout.bodies):
            assert data[offset] == phrase.length
            assert data[offset + 1 : offset + 1 + phrase.length] == phrase.body

    def test_the_entries_stand_where_the_table_states(self) -> None:
        song = spelled_phrase_song()
        data = song_to_bytes(song, PROGRAM_AREA_BYTES)
        table = read_word(data, PHRASE_TABLE_OFFSET)
        stated = read_words(data, table + 1, len(song.planes.phrases))
        assert stated == SongLayout.of(song).bodies


def spelled_phrase_song() -> Song:
    """A song whose figure repeats often enough for the dictionary to hold it."""
    figure = (SOUNDING, OCTAVE_UP, RESTING, OCTAVE_UP)
    return player_song(resting_streams(figure * 8), NTSC_FREQUENCY, loop_tick=None)


class TestStreamOffsets:
    """Every plane's stream is found where the header says it is."""

    def test_the_first_stream_begins_past_the_dictionary(self) -> None:
        song = two_tick_song(NTSC_FREQUENCY)
        data = song_to_bytes(song, PROGRAM_AREA_BYTES)
        assert stream_offsets(data)[0] == SongLayout.of(song).streams[0]

    def test_the_offsets_ascend_in_plane_order(self) -> None:
        data = song_to_bytes(two_tick_song(NTSC_FREQUENCY), PROGRAM_AREA_BYTES)
        offsets = stream_offsets(data)
        assert list(offsets) == sorted(offsets)

    def test_each_offset_lands_on_that_planes_first_token(self) -> None:
        song = two_tick_song(NTSC_FREQUENCY)
        data = song_to_bytes(song, PROGRAM_AREA_BYTES)
        for offset, stream in zip(stream_offsets(data), song.planes.streams):
            assert data[offset : offset + len(stream)] == stream

    def test_the_streams_fill_the_song_to_its_last_byte(self) -> None:
        song = two_tick_song(NTSC_FREQUENCY)
        data = song_to_bytes(song, PROGRAM_AREA_BYTES)
        assert len(data) == stream_offsets(data)[-1] + len(song.planes.streams[-1])


class TestLoopEntries:
    """Where each plane's stream is re-entered once the song repeats."""

    def test_a_song_that_repeats_states_the_token_its_loop_tick_starts(self) -> None:
        song = repeating_song()
        data = song_to_bytes(song, PROGRAM_AREA_BYTES)
        entered = song.planes.entries(LOOP_TICK)
        assert loop_entries(data) == tuple(offset + entry for offset, entry in zip(stream_offsets(data), entered))

    def test_a_song_that_stops_re_enters_at_its_own_first_token(self) -> None:
        data = song_to_bytes(two_tick_song(NTSC_FREQUENCY), PROGRAM_AREA_BYTES)
        assert loop_entries(data) == stream_offsets(data)

    def test_every_entry_lands_on_a_token_the_stream_holds(self) -> None:
        song = repeating_song()
        data = song_to_bytes(song, PROGRAM_AREA_BYTES)
        for entry, offset, stream in zip(loop_entries(data), stream_offsets(data), song.planes.streams):
            assert offset <= entry < offset + len(stream)


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

    def test_a_song_reaching_past_the_offset_field_names_what_overflowed(self) -> None:
        """A block given exactly the room it takes is still refused where an offset overflows."""
        song = spelled_song(MAX_BLOCK_OFFSET, NTSC_FREQUENCY)
        with pytest.raises(SongTooLargeError) as overflow:
            song_to_bytes(song, SongLayout.of(song).size)

        named = [plane.replace(NAME_SEPARATOR, " ") for plane in PlaneOrder.names()]
        assert any(plane in str(overflow.value) for plane in named)
