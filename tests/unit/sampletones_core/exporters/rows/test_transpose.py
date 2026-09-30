from typing import Dict, Final, FrozenSet, List, Optional, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.rows.levels import RowPlace
from sampletones_core.exporters.rows.transpose import (
    NOTE_TRANSPOSE,
    Repitch,
    SoundingNote,
    sounding_notes,
)
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn

ROWS_PER_PATTERN: Final[int] = 4
VOICE: Final[str] = "voice"
SILENT_VOICE: Final[str] = "silent"
CHANNEL: Final[ChannelName] = ChannelName.PULSE1
NOTE_ON_TRANSPOSE: Final[int] = 5
RAISED: Final[int] = 2
LOWERED: Final[int] = -3
INSTRUMENTS: Final[FrozenSet[Tuple[str, ChannelName]]] = frozenset({(VOICE, CHANNEL)})


def _song(
    patterns: Dict[int, List[Row]],
    order: List[Optional[int]],
) -> Song:
    """A song of one channel's patterns, every other channel left empty."""
    pools = {
        channel_name: Channel(
            name=channel_name,
            patterns=(
                {index: Pattern(rows=rows) for index, rows in patterns.items()} if channel_name == CHANNEL else {}
            ),
        )
        for channel_name in ChannelName.items()
    }
    return Song(
        rows_per_pattern=ROWS_PER_PATTERN,
        order=[{CHANNEL: index} for index in order],
        channels=pools,
    )


def _rows(*cells: Tuple[int, Row]) -> List[Row]:
    rows = [Row() for _ in range(ROWS_PER_PATTERN)]
    for row_index, row in cells:
        rows[row_index] = row

    return rows


def _place(order_position: int, pattern_index: int, row_index: int) -> RowPlace:
    return RowPlace(order_position=order_position, pattern_index=pattern_index, row_index=row_index)


def _note(transpose: Optional[int] = None) -> Row:
    return Row(command=NoteOn(voice_id=VOICE), transpose=transpose)


class TestTheNotesATransposeRowMoves:
    """A row stating a transpose and no note moves the note already sounding, which keeps playing
    from the tick it reached, so the walk names each such row beside the note it moves and how long
    that note has sounded.
    """

    def test_a_transpose_row_reaches_the_note_before_it(self) -> None:
        song = _song({0: _rows((0, _note()), (2, Row(transpose=RAISED)))}, [0])

        assert sounding_notes(song, CHANNEL, INSTRUMENTS) == (
            SoundingNote(
                place=_place(0, 0, 0),
                voice_id=VOICE,
                transpose=NOTE_TRANSPOSE,
                repitches=(Repitch(place=_place(0, 0, 2), transpose=RAISED, rows=2),),
            ),
        )

    def test_the_note_keeps_the_transpose_its_own_row_states(self) -> None:
        song = _song({0: _rows((0, _note(NOTE_ON_TRANSPOSE)), (1, Row(transpose=RAISED)))}, [0])

        (note,) = sounding_notes(song, CHANNEL, INSTRUMENTS)

        assert note.transpose == NOTE_ON_TRANSPOSE

    def test_every_transpose_row_of_a_note_is_named_in_the_order_the_song_plays_them(self) -> None:
        song = _song({0: _rows((0, _note()), (1, Row(transpose=RAISED)), (3, Row(transpose=LOWERED)))}, [0])

        (note,) = sounding_notes(song, CHANNEL, INSTRUMENTS)

        assert [(repitch.transpose, repitch.rows) for repitch in note.repitches] == [(RAISED, 1), (LOWERED, 3)]

    def test_a_note_is_counted_across_frames(self) -> None:
        """A frame plays a whole pattern, so a transpose row in a later frame counts every row between."""
        song = _song({0: _rows((1, _note())), 1: _rows((2, Row(transpose=RAISED)))}, [0, 1])

        (note,) = sounding_notes(song, CHANNEL, INSTRUMENTS)

        assert note.repitches == (Repitch(place=_place(1, 1, 2), transpose=RAISED, rows=5),)

    def test_a_frame_leaving_the_channel_empty_keeps_the_note_sounding(self) -> None:
        song = _song({0: _rows((0, _note())), 1: _rows((1, Row(transpose=RAISED)))}, [0, None, 1])

        (note,) = sounding_notes(song, CHANNEL, INSTRUMENTS)

        assert note.repitches[0].rows == 2 * ROWS_PER_PATTERN + 1

    def test_a_pattern_the_order_plays_twice_is_reached_in_each_frame(self) -> None:
        song = _song({0: _rows((0, _note()), (2, Row(transpose=RAISED)))}, [0, 0])

        notes = sounding_notes(song, CHANNEL, INSTRUMENTS)

        assert [note.place.order_position for note in notes] == [0, 1]

    def test_a_note_off_ends_the_note(self) -> None:
        song = _song({0: _rows((0, _note()), (1, Row(command=NoteOff())), (2, Row(transpose=RAISED)))}, [0])

        assert sounding_notes(song, CHANNEL, INSTRUMENTS) == ()

    def test_a_note_the_channel_has_no_instrument_for_moves_nothing(self) -> None:
        """Such a note-on is written as a note cut, so the channel is silent when the row comes."""
        song = _song(
            {0: _rows((0, Row(command=NoteOn(voice_id=SILENT_VOICE))), (2, Row(transpose=RAISED)))},
            [0],
        )

        assert sounding_notes(song, CHANNEL, INSTRUMENTS) == ()

    def test_a_transpose_row_before_any_note_moves_nothing(self) -> None:
        song = _song({0: _rows((0, Row(transpose=RAISED)), (2, _note()))}, [0])

        assert sounding_notes(song, CHANNEL, INSTRUMENTS) == ()

    def test_a_note_no_transpose_row_reaches_is_left_out(self) -> None:
        song = _song({0: _rows((0, _note()), (1, Row(volume=RAISED)), (2, _note()), (3, Row(transpose=RAISED)))}, [0])

        (note,) = sounding_notes(song, CHANNEL, INSTRUMENTS)

        assert note.place == _place(0, 0, 2)
