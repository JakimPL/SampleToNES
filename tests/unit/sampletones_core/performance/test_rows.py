from dataclasses import dataclass
from typing import Optional, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.performance import ChannelPerformance, apply_row, resolve_row
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_core.project.song_position import SongPosition
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

ROWS_PER_PATTERN: int = 4
SOUNDING_ROW: int = 2
SAMPLE_ID: str = "sample"
ANOTHER_SAMPLE_ID: str = "another"


def _song() -> Song:
    """A one-frame song whose pulse pattern names a sample on ``SOUNDING_ROW``."""
    song = Song.empty(ROWS_PER_PATTERN)
    pattern = song.channels[ChannelName.PULSE1].patterns[0]
    pattern.rows[SOUNDING_ROW] = Row(
        command=Instrument(sample_id=SAMPLE_ID, channel_name=ChannelName.PULSE1),
    )
    return song


class TestResolveRow(BaseTestSuite):
    """Which row a channel reaches, over every way an order position answers with none."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: bool
        position: SongPosition
        order_entry: Optional[int]

    test_cases: Tuple["TestResolveRow.TestCase", ...] = (
        TestCase(
            label="the row the pattern states",
            position=SongPosition(order_position=0, row_index=SOUNDING_ROW),
            order_entry=0,
            expected=True,
        ),
        TestCase(
            label="a position past the order's end",
            position=SongPosition(order_position=1, row_index=SOUNDING_ROW),
            order_entry=0,
            expected=False,
        ),
        TestCase(
            label="a silent slot",
            position=SongPosition(order_position=0, row_index=SOUNDING_ROW),
            order_entry=None,
            expected=False,
        ),
        TestCase(
            label="a slot naming a pattern the pool has none of",
            position=SongPosition(order_position=0, row_index=SOUNDING_ROW),
            order_entry=7,
            expected=False,
        ),
        TestCase(
            label="a row past the pattern's length",
            position=SongPosition(order_position=0, row_index=ROWS_PER_PATTERN),
            order_entry=0,
            expected=False,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_row_a_position_answers_with(self, test_case: TestCase) -> None:
        song = _song()
        song.set_order_entry(0, ChannelName.PULSE1, test_case.order_entry)

        row = resolve_row(song, test_case.position, ChannelName.PULSE1)

        assert (row is not None) is test_case.expected

    def test_an_empty_row_is_answered_with_rather_than_skipped(self) -> None:
        """A row stating nothing is still a row, which is what keeps a channel's state its own."""
        song = _song()

        row = resolve_row(song, SongPosition(order_position=0, row_index=0), ChannelName.PULSE1)

        assert row == Row()


class TestApplyRow(BaseTestSuite):
    """What a row leaves the channel carrying, and whether the note starts over."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: bool
        row: Row
        sample_id: Optional[str]
        transpose: int
        volume: int

    test_cases: Tuple["TestApplyRow.TestCase", ...] = (
        TestCase(
            label="a note column with no modifiers takes the defaults",
            row=Row(command=Instrument(sample_id=SAMPLE_ID, channel_name=ChannelName.PULSE1)),
            sample_id=SAMPLE_ID,
            transpose=0,
            volume=MAX_VOLUME,
            expected=True,
        ),
        TestCase(
            label="a note column takes the modifiers the row states",
            row=Row(
                command=Instrument(sample_id=SAMPLE_ID, channel_name=ChannelName.PULSE1),
                transpose=5,
                volume=8,
            ),
            sample_id=SAMPLE_ID,
            transpose=5,
            volume=8,
            expected=True,
        ),
        TestCase(
            label="a note off silences the channel",
            row=Row(command=NoteOff()),
            sample_id=None,
            transpose=3,
            volume=8,
            expected=True,
        ),
        TestCase(
            label="an empty row leaves everything as it stands",
            row=Row(),
            sample_id=ANOTHER_SAMPLE_ID,
            transpose=3,
            volume=8,
            expected=False,
        ),
        TestCase(
            label="a modifier row bends the note already sounding",
            row=Row(transpose=-2, volume=4),
            sample_id=ANOTHER_SAMPLE_ID,
            transpose=-2,
            volume=4,
            expected=False,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_what_the_channel_carries_after_the_row(self, test_case: TestCase) -> None:
        performance = ChannelPerformance(
            sample_id=ANOTHER_SAMPLE_ID,
            tick_index=6,
            transpose=3,
            volume=8,
        )

        retriggered = apply_row(performance, test_case.row)

        assert retriggered is test_case.expected
        assert performance.sample_id == test_case.sample_id
        assert performance.transpose == test_case.transpose
        assert performance.volume == test_case.volume

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_tick_index_returns_to_the_start_exactly_where_the_note_does(
        self,
        test_case: TestCase,
    ) -> None:
        """A row that starts the note over is a row that starts its envelopes over."""
        performance = ChannelPerformance(sample_id=ANOTHER_SAMPLE_ID, tick_index=6)

        retriggered = apply_row(performance, test_case.row)

        assert (performance.tick_index == 0) is retriggered
