from typing import Dict, List, Optional, Set, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.skipped import SkippedRow, find_skipped_rows
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn

ROWS_PER_PATTERN = 4
KNOWN = "known"
UNKNOWN = "unknown"


def _song(
    channels: Dict[ChannelName, Dict[int, List[Row]]],
    order: List[Dict[ChannelName, Optional[int]]],
) -> Song:
    pools = {
        channel_name: Channel(
            name=channel_name,
            patterns={index: Pattern(rows=rows) for index, rows in channels.get(channel_name, {}).items()},
        )
        for channel_name in ChannelName.items()
    }
    return Song(rows_per_pattern=ROWS_PER_PATTERN, order=order, channels=pools)


def _rows(**commands: NoteOn) -> List[Row]:
    rows = [Row() for _ in range(ROWS_PER_PATTERN)]
    for position, command in commands.items():
        rows[int(position.removeprefix("row_"))] = Row(command=command)

    return rows


INSTRUMENTS: Set[Tuple[str, ChannelName]] = {(KNOWN, ChannelName.PULSE1)}


class TestFindingTheRowsLeftSilent:
    def test_a_note_on_naming_a_voice_without_an_instrument_on_its_channel_is_found(self) -> None:
        song = _song(
            {ChannelName.PULSE2: {0: _rows(row_1=NoteOn(voice_id=KNOWN))}},
            [{ChannelName.PULSE2: 0}],
        )

        assert find_skipped_rows(song, INSTRUMENTS) == (
            SkippedRow(voice_id=KNOWN, channel=ChannelName.PULSE2, order_position=0, row_index=1),
        )

    def test_a_note_on_with_an_instrument_on_its_channel_is_left_alone(self) -> None:
        song = _song(
            {ChannelName.PULSE1: {0: _rows(row_1=NoteOn(voice_id=KNOWN))}},
            [{ChannelName.PULSE1: 0}],
        )

        assert find_skipped_rows(song, INSTRUMENTS) == ()

    def test_a_note_off_is_left_alone(self) -> None:
        rows = _rows()
        rows[2] = Row(command=NoteOff())
        song = _song({ChannelName.PULSE2: {0: rows}}, [{ChannelName.PULSE2: 0}])

        assert find_skipped_rows(song, INSTRUMENTS) == ()

    def test_a_pattern_the_order_plays_twice_is_found_in_each_frame(self) -> None:
        song = _song(
            {ChannelName.PULSE2: {0: _rows(row_0=NoteOn(voice_id=UNKNOWN))}},
            [{ChannelName.PULSE2: 0}, {ChannelName.PULSE2: None}, {ChannelName.PULSE2: 0}],
        )

        assert [row.order_position for row in find_skipped_rows(song, INSTRUMENTS)] == [0, 2]

    def test_a_pattern_no_frame_plays_is_not_found(self) -> None:
        song = _song(
            {ChannelName.PULSE2: {0: _rows(row_0=NoteOn(voice_id=UNKNOWN))}},
            [{ChannelName.PULSE2: None}],
        )

        assert find_skipped_rows(song, INSTRUMENTS) == ()

    def test_the_rows_come_in_the_order_the_song_plays_them(self) -> None:
        song = _song(
            {
                ChannelName.PULSE2: {0: _rows(row_3=NoteOn(voice_id=UNKNOWN))},
                ChannelName.TRIANGLE: {0: _rows(row_0=NoteOn(voice_id=UNKNOWN))},
            },
            [{ChannelName.PULSE2: 0, ChannelName.TRIANGLE: 0}, {ChannelName.PULSE2: 0}],
        )

        found = [(row.order_position, row.channel, row.row_index) for row in find_skipped_rows(song, INSTRUMENTS)]

        assert found == [
            (0, ChannelName.PULSE2, 3),
            (0, ChannelName.TRIANGLE, 0),
            (1, ChannelName.PULSE2, 3),
        ]
