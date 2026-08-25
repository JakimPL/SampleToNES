from typing import Final

from sampletones_player.nsf.layout import SongLayout
from sampletones_player.song import Song
from sampletones_player.specification.compression import (
    PHRASE_LENGTH_SIZE,
    PHRASE_TABLE_COUNT_SIZE,
    PHRASE_TABLE_ENTRY_SIZE,
    PLANE_COUNT,
)
from sampletones_player.specification.song import SONG_HEADER_SIZE
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
LOOP_TICK: Final[int] = 2
FIGURE_REPEATS: Final[int] = 8

SOUNDING: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_REFERENCE_TIMER)
RESTING: Final = pulse_tick(PLAYER_SILENT_VOLUME, 0, PLAYER_REFERENCE_TIMER)
OCTAVE_UP: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_OCTAVE_UP_TIMER)

FIGURE: Final = (SOUNDING, OCTAVE_UP, RESTING, OCTAVE_UP)


def figure_song(loop_tick: int) -> Song:
    return player_song(resting_streams(FIGURE * FIGURE_REPEATS), NTSC_FREQUENCY, loop_tick=loop_tick)


class TestWhereEachPartOfTheBlockBegins:
    """The parts follow one another in the order the block writes them, none of them overlapping."""

    def test_the_timer_table_follows_the_header(self) -> None:
        assert SongLayout.of(figure_song(LOOP_TICK)).timer_table == SONG_HEADER_SIZE

    def test_the_dictionary_follows_the_timer_table(self) -> None:
        song = figure_song(LOOP_TICK)
        layout = SongLayout.of(song)
        assert layout.phrase_table == layout.timer_table + len(song.pitches.data)

    def test_the_first_body_follows_the_table_of_entries(self) -> None:
        song = figure_song(LOOP_TICK)
        layout = SongLayout.of(song)
        entries = PHRASE_TABLE_COUNT_SIZE + PHRASE_TABLE_ENTRY_SIZE * len(song.planes.phrases)
        assert layout.bodies[0] == layout.phrase_table + entries

    def test_each_body_follows_the_one_before_it(self) -> None:
        song = figure_song(LOOP_TICK)
        layout = SongLayout.of(song)
        for phrase, offset, following in zip(song.planes.phrases.phrases, layout.bodies, layout.bodies[1:]):
            assert following == offset + PHRASE_LENGTH_SIZE + phrase.length

    def test_the_first_stream_follows_the_last_body(self) -> None:
        song = figure_song(LOOP_TICK)
        layout = SongLayout.of(song)
        last = song.planes.phrases[len(song.planes.phrases) - 1]
        assert layout.streams[0] == layout.bodies[-1] + PHRASE_LENGTH_SIZE + last.length

    def test_each_stream_follows_the_one_before_it(self) -> None:
        song = figure_song(LOOP_TICK)
        layout = SongLayout.of(song)
        for stream, offset, following in zip(song.planes.streams, layout.streams, layout.streams[1:]):
            assert following == offset + len(stream)

    def test_the_block_ends_behind_the_last_stream(self) -> None:
        song = figure_song(LOOP_TICK)
        layout = SongLayout.of(song)
        assert layout.size == layout.streams[-1] + len(song.planes.streams[-1])


class TestWhereEachStreamIsReEntered:
    """A loop entry stands inside the stream it belongs to, at the token its tick starts."""

    def test_every_plane_states_an_entry(self) -> None:
        assert len(SongLayout.of(figure_song(LOOP_TICK)).loop_entries) == PLANE_COUNT

    def test_an_entry_stands_at_the_token_the_loop_tick_starts(self) -> None:
        song = figure_song(LOOP_TICK)
        layout = SongLayout.of(song)
        entered = song.planes.entries(LOOP_TICK)
        assert layout.loop_entries == tuple(offset + entry for offset, entry in zip(layout.streams, entered))

    def test_a_song_that_stops_re_enters_at_each_streams_own_start(self) -> None:
        song = player_song(resting_streams(FIGURE * FIGURE_REPEATS), NTSC_FREQUENCY, loop_tick=None)
        layout = SongLayout.of(song)
        assert layout.loop_entries == layout.streams


class TestWhatTheBlockStates:
    """Every offset written into the block is named, so an overflow says which part reached past."""

    def test_every_part_of_the_block_is_named(self) -> None:
        song = figure_song(LOOP_TICK)
        layout = SongLayout.of(song)
        expected = 2 + len(song.planes.phrases) + 2 * PLANE_COUNT
        assert len(layout.stated) == expected

    def test_every_stated_offset_lies_inside_the_block(self) -> None:
        layout = SongLayout.of(figure_song(LOOP_TICK))
        assert all(0 < offset < layout.size for _, offset in layout.stated)
