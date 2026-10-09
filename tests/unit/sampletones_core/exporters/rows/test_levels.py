from dataclasses import dataclass
from typing import Dict, Final, List, Optional, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME, SILENT_VOLUME
from sampletones_core.exporters.rows.levels import RowPlace, cell_volume, full_level_notes
from sampletones_core.performance.modifiers import TRIANGLE_LOUDEST_SILENT_VOLUME
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.pitch import Step
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

ROWS_PER_PATTERN: Final[int] = 4
VOICE: Final[str] = "voice"
CHANNEL: Final[ChannelName] = ChannelName.PULSE1
QUIET_VOLUME: Final[int] = 5
LOUD_VOLUME: Final[int] = 12
TRANSPOSE: Final[int] = 3

NOTE: Final[Row] = Row(command=NoteOn(voice_id=VOICE))
QUIET_ROW: Final[Row] = Row(volume=QUIET_VOLUME)
FULL_ROW: Final[Row] = Row(volume=MAX_VOLUME)


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


class TestTheNotesWritingTheFullLevel:
    """The song starts a note at the full level wherever its row states none, while a tracker carries
    the last level its column wrote into the note, so such a note is written at the full level
    wherever the tracker would carry another into it.
    """

    def test_a_note_after_a_quieter_row_writes_the_full_level(self) -> None:
        song = _song({0: _rows((0, QUIET_ROW), (2, NOTE))}, [0])

        assert full_level_notes(song, CHANNEL) == {_place(0, 0, 2)}

    def test_a_note_the_channel_reaches_at_the_full_level_writes_nothing(self) -> None:
        song = _song({0: _rows((0, FULL_ROW), (2, NOTE))}, [0])

        assert full_level_notes(song, CHANNEL) == frozenset()

    def test_a_note_stating_its_own_level_writes_nothing_more(self) -> None:
        song = _song({0: _rows((0, QUIET_ROW), (2, Row(command=NoteOn(voice_id=VOICE), volume=LOUD_VOLUME)))}, [0])

        assert full_level_notes(song, CHANNEL) == frozenset()

    def test_a_note_after_one_the_song_starts_at_full_writes_nothing(self) -> None:
        """A note whose row states no level leaves the tracker at the full level too."""
        song = _song({0: _rows((0, QUIET_ROW), (1, NOTE), (3, NOTE))}, [0])

        assert full_level_notes(song, CHANNEL) == {_place(0, 0, 1)}

    def test_a_note_off_stating_a_level_is_carried_into_the_next_note(self) -> None:
        """The song leaves the level alone on a note-off, while the tracker's column takes the level
        its cell writes, so the next note is reached at that level.
        """
        song = _song({0: _rows((0, NOTE), (1, Row(command=NoteOff(), volume=QUIET_VOLUME)), (3, NOTE))}, [0])

        assert full_level_notes(song, CHANNEL) == {_place(0, 0, 3)}

    def test_a_transpose_alone_leaves_the_level_alone(self) -> None:
        song = _song({0: _rows((0, QUIET_ROW), (1, Row(pitch=Step(value=TRANSPOSE))), (2, NOTE))}, [0])

        assert full_level_notes(song, CHANNEL) == {_place(0, 0, 2)}

    def test_the_level_crosses_into_the_next_frame(self) -> None:
        song = _song({0: _rows((3, QUIET_ROW)), 1: _rows((0, NOTE))}, [0, 1])

        assert full_level_notes(song, CHANNEL) == {_place(1, 1, 0)}

    def test_the_level_crosses_a_frame_the_channel_rests_in(self) -> None:
        song = _song({0: _rows((3, QUIET_ROW)), 1: _rows((0, NOTE))}, [0, None, 1])

        assert full_level_notes(song, CHANNEL) == {_place(2, 1, 0)}

    def test_the_level_the_song_ends_on_reaches_its_first_note(self) -> None:
        """A tracker returns to the first frame at the end of the order, keeping the level the
        channel was left at, so the song's first note is reached at the level it ends on.
        """
        song = _song({0: _rows((0, NOTE), (3, QUIET_ROW))}, [0])

        assert full_level_notes(song, CHANNEL) == {_place(0, 0, 0)}

    def test_a_pattern_is_reached_in_every_frame_that_plays_it(self) -> None:
        song = _song({0: _rows((0, NOTE)), 1: _rows((0, QUIET_ROW))}, [0, 1, 0])

        assert full_level_notes(song, CHANNEL) == {_place(2, 0, 0)}

    def test_a_song_stating_no_level_writes_none(self) -> None:
        song = _song({0: _rows((0, NOTE), (2, NOTE))}, [0, 0])

        assert full_level_notes(song, CHANNEL) == frozenset()


class TestTheLevelACellStates(BaseTestSuite):
    """A cell states the row's own level, the full level on a note that writes it, and nothing
    otherwise; the triangle states silence at a level the song rests it at.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        row: Row
        channel_name: ChannelName
        full_level: bool
        expected: Optional[int]

    test_cases: Tuple["TestTheLevelACellStates.TestCase", ...] = (
        TestCase(
            label="a stated level",
            row=QUIET_ROW,
            channel_name=CHANNEL,
            full_level=False,
            expected=QUIET_VOLUME,
        ),
        TestCase(
            label="a note writing the full level",
            row=NOTE,
            channel_name=CHANNEL,
            full_level=True,
            expected=MAX_VOLUME,
        ),
        TestCase(
            label="a note carrying the level",
            row=NOTE,
            channel_name=CHANNEL,
            full_level=False,
            expected=None,
        ),
        TestCase(
            label="silence",
            row=Row(volume=SILENT_VOLUME),
            channel_name=CHANNEL,
            full_level=False,
            expected=SILENT_VOLUME,
        ),
        TestCase(
            label="a quiet level on the pulse",
            row=Row(volume=TRIANGLE_LOUDEST_SILENT_VOLUME),
            channel_name=CHANNEL,
            full_level=False,
            expected=TRIANGLE_LOUDEST_SILENT_VOLUME,
        ),
        TestCase(
            label="the loudest level the triangle rests at",
            row=Row(volume=TRIANGLE_LOUDEST_SILENT_VOLUME),
            channel_name=ChannelName.TRIANGLE,
            full_level=False,
            expected=SILENT_VOLUME,
        ),
        TestCase(
            label="the quietest level the triangle sounds at",
            row=Row(volume=TRIANGLE_LOUDEST_SILENT_VOLUME + 1),
            channel_name=ChannelName.TRIANGLE,
            full_level=False,
            expected=TRIANGLE_LOUDEST_SILENT_VOLUME + 1,
        ),
        TestCase(
            label="a triangle note writing the full level",
            row=NOTE,
            channel_name=ChannelName.TRIANGLE,
            full_level=True,
            expected=MAX_VOLUME,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_cell_states_the_level(self, test_case: "TestTheLevelACellStates.TestCase") -> None:
        assert cell_volume(test_case.row, test_case.channel_name, full_level=test_case.full_level) == test_case.expected
