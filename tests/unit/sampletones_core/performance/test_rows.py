from dataclasses import dataclass
from typing import Dict, Final, Optional, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.features import CHANNEL_FEATURE_DEFAULTS
from sampletones_core.performance import (
    ChannelPerformance,
    VoiceReading,
    apply_row,
    resolve_row,
    sound_tick,
)
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_core.project.song_position import SongPosition
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.sample import Sample
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.performance import make_pulse_reconstruction

ROWS_PER_PATTERN: int = 4
SOUNDING_ROW: int = 2
SAMPLE_ID: str = "sample"
ANOTHER_SAMPLE_ID: str = "another"
QUIET_VOLUME: Final[int] = 3
LEFT_BEHIND: Final[Dict[FeatureKey, int]] = {
    FeatureKey.VOLUME: 0,
    FeatureKey.ARPEGGIO: 7,
    FeatureKey.PITCH: -3,
    FeatureKey.HI_PITCH: 1,
    FeatureKey.DUTY_CYCLE: 2,
}


def _song() -> Song:
    """A one-frame song whose pulse pattern names a sample on ``SOUNDING_ROW``."""
    song = Song.empty(ROWS_PER_PATTERN)
    pattern = song.channels[ChannelName.PULSE1].patterns[0]
    pattern.rows[SOUNDING_ROW] = Row(
        command=NoteOn(voice_id=SAMPLE_ID),
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
        voice_id: Optional[str]
        transpose: int
        volume: int

    test_cases: Tuple["TestApplyRow.TestCase", ...] = (
        TestCase(
            label="a note column with no modifiers takes the defaults",
            row=Row(command=NoteOn(voice_id=SAMPLE_ID)),
            voice_id=SAMPLE_ID,
            transpose=0,
            volume=MAX_VOLUME,
            expected=True,
        ),
        TestCase(
            label="a note column takes the modifiers the row states",
            row=Row(
                command=NoteOn(voice_id=SAMPLE_ID),
                transpose=5,
                volume=8,
            ),
            voice_id=SAMPLE_ID,
            transpose=5,
            volume=8,
            expected=True,
        ),
        TestCase(
            label="a note off silences the channel",
            row=Row(command=NoteOff()),
            voice_id=None,
            transpose=3,
            volume=8,
            expected=True,
        ),
        TestCase(
            label="an empty row leaves everything as it stands",
            row=Row(),
            voice_id=ANOTHER_SAMPLE_ID,
            transpose=3,
            volume=8,
            expected=False,
        ),
        TestCase(
            label="a modifier row bends the note already sounding",
            row=Row(transpose=-2, volume=4),
            voice_id=ANOTHER_SAMPLE_ID,
            transpose=-2,
            volume=4,
            expected=False,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_what_the_channel_carries_after_the_row(self, test_case: TestCase) -> None:
        performance = ChannelPerformance(
            voice_id=ANOTHER_SAMPLE_ID,
            tick_index=6,
            transpose=3,
            volume=8,
        )

        retriggered = apply_row(performance, test_case.row)

        assert retriggered is test_case.expected
        assert performance.voice_id == test_case.voice_id
        assert performance.transpose == test_case.transpose
        assert performance.volume == test_case.volume

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_tick_index_returns_to_the_start_exactly_where_the_note_does(
        self,
        test_case: TestCase,
    ) -> None:
        """A row that starts the note over is a row that starts its envelopes over."""
        performance = ChannelPerformance(voice_id=ANOTHER_SAMPLE_ID, tick_index=6)

        retriggered = apply_row(performance, test_case.row)

        assert (performance.tick_index == 0) is retriggered


class TestANoteStartsItsDimensionsOver(BaseTestSuite):
    """A note starts every envelope dimension from where a song starts, whatever the one before it left.

    A row naming no note plays on inside the note already sounding, so it leaves the dimensions
    where that note has taken them.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        row: Row
        expected: Dict[FeatureKey, int]

    test_cases: Tuple["TestANoteStartsItsDimensionsOver.TestCase", ...] = (
        TestCase(
            label="a note column",
            row=Row(command=NoteOn(voice_id=SAMPLE_ID)),
            expected=CHANNEL_FEATURE_DEFAULTS,
        ),
        TestCase(
            label="a note column with modifiers",
            row=Row(
                command=NoteOn(voice_id=SAMPLE_ID),
                transpose=5,
                volume=8,
            ),
            expected=CHANNEL_FEATURE_DEFAULTS,
        ),
        TestCase(
            label="an empty row",
            row=Row(),
            expected=LEFT_BEHIND,
        ),
        TestCase(
            label="a modifier row",
            row=Row(transpose=-2, volume=4),
            expected=LEFT_BEHIND,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_dimensions_the_channel_carries_after_the_row(self, test_case: TestCase) -> None:
        performance = ChannelPerformance(
            voice_id=ANOTHER_SAMPLE_ID,
            tick_index=6,
            feature_values=LEFT_BEHIND.copy(),
        )

        apply_row(performance, test_case.row)

        assert performance.feature_values == test_case.expected

    def test_a_note_leaves_the_defaults_themselves_untouched(self) -> None:
        """Each note takes a copy, so what a note writes reaches neither the next nor a song's start."""
        defaults = dict(CHANNEL_FEATURE_DEFAULTS)
        performance = ChannelPerformance(voice_id=ANOTHER_SAMPLE_ID)
        apply_row(performance, Row(command=NoteOn(voice_id=SAMPLE_ID)))

        performance.feature_values[FeatureKey.ARPEGGIO] += 1

        assert CHANNEL_FEATURE_DEFAULTS == defaults

    def test_a_sample_holding_its_level_after_a_quieter_one_sounds_at_full_volume(self) -> None:
        """A level one sample wrote ends with its note, so the next leaves its level where a song starts."""
        writes = Sample(name="writes", reconstruction=make_pulse_reconstruction(volume=QUIET_VOLUME))
        holds = Sample(
            name="holds",
            reconstruction=make_pulse_reconstruction(
                volume=MAX_VOLUME,
                held_features=(FeatureKey.VOLUME,),
            ),
        )
        writes_reading = VoiceReading.read(writes, ChannelName.PULSE1)
        holds_reading = VoiceReading.read(holds, ChannelName.PULSE1)
        assert writes_reading is not None and holds_reading is not None

        performance = ChannelPerformance()
        apply_row(performance, Row(command=NoteOn(voice_id=writes.id)))
        sound_tick(performance, writes_reading)
        apply_row(performance, Row(command=NoteOn(voice_id=holds.id)))
        sounded = sound_tick(performance, holds_reading)

        assert sounded is not None and sounded.on is True
        assert performance.feature_values[FeatureKey.VOLUME] == MAX_VOLUME
