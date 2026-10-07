from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, Final, Optional, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.constants.general import MAX_VOLUME, NUM_PERIODS
from sampletones_core.features import CHANNEL_FEATURE_DEFAULTS
from sampletones_core.features.envelope import Envelope
from sampletones_core.performance import (
    ChannelPerformance,
    VoiceReading,
    apply_row,
    resolve_row,
    sound_tick,
    sounding_pitch,
)
from sampletones_core.project.patterns.pitch import Note, Step
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_core.project.song_position import SongPosition
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceLookup, VoiceUnion, voice_reference
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.performance import make_noise_reconstruction, make_pulse_reconstruction

ROWS_PER_PATTERN: int = 4
SOUNDING_ROW: int = 2
SAMPLE_ID: str = "sample"
ANOTHER_SAMPLE_ID: str = "another"
GONE_ID: Final[str] = "gone"
QUIET_VOLUME: Final[int] = 3
LOW_VOLUME: Final[int] = 8
PLAYED_OUT: Final[int] = 999
LEFT_BEHIND: Final[Dict[FeatureKey, int]] = {
    FeatureKey.VOLUME: 0,
    FeatureKey.ARPEGGIO: 7,
    FeatureKey.PITCH: -3,
    FeatureKey.HI_PITCH: 1,
    FeatureKey.DUTY_CYCLE: 2,
}
SAMPLE_PITCH: Final[int] = 60
DRUM_PERIOD: Final[int] = 3
LEAD_PITCH: Final[int] = 60
LEAD_PERIOD: Final[int] = 5
TYPED_NOTE: Final[int] = 67
TYPED_PERIOD: Final[int] = 9
STEP_UP: Final[int] = 5
STEP_DOWN: Final[int] = -2
SOUNDING_STEP: Final[int] = 7
PERIOD_STEP: Final[int] = 14

SAMPLE: Final[Sample] = Sample(name=SAMPLE_ID, reconstruction=make_pulse_reconstruction(pitch=SAMPLE_PITCH))
ANOTHER: Final[Sample] = Sample(name=ANOTHER_SAMPLE_ID, reconstruction=make_pulse_reconstruction(pitch=SAMPLE_PITCH))
DRUM: Final[Sample] = Sample(name="drum", reconstruction=make_noise_reconstruction(period=DRUM_PERIOD))
LEAD: Final[Instrument] = Instrument(
    name="lead",
    envelopes=InstrumentEnvelopes(volume=Envelope(items=(MAX_VOLUME,))),
    initial_pitch=LEAD_PITCH,
    initial_period=LEAD_PERIOD,
)
VOICES: Final[Dict[str, VoiceUnion]] = {voice.id: voice for voice in (SAMPLE, ANOTHER, DRUM, LEAD)}
LOOKUP: Final[VoiceLookup] = VOICES.get


def _song() -> Song:
    """A one-frame song whose pulse pattern names a sample on ``SOUNDING_ROW``."""
    song = Song.empty(ROWS_PER_PATTERN)
    pattern = song.channels[ChannelName.PULSE1].patterns[0]
    pattern.rows[SOUNDING_ROW] = Row(
        command=NoteOn(voice_id=SAMPLE.id),
    )
    return song


def _silent(*, transpose: int = 0, volume: int = MAX_VOLUME) -> ChannelPerformance:
    return ChannelPerformance(transpose=transpose, volume=volume)


def _sounding(
    voice_id: str,
    *,
    transpose: int = SOUNDING_STEP,
    volume: int = LOW_VOLUME,
    tick_index: int = 6,
) -> ChannelPerformance:
    return ChannelPerformance(voice_id=voice_id, tick_index=tick_index, transpose=transpose, volume=volume)


def _reference(voice: VoiceUnion, channel_name: ChannelName = ChannelName.PULSE1) -> int:
    return voice_reference(voice, channel_name)


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
    """What a row leaves the channel carrying, and whether the note starts over.

    A note-on with a pitch starts the voice there, whichever face the pitch was written in. A
    sample without one plays as recorded. An instrument without one goes on from the pitch the
    channel is sounding, whatever voice sounded it, and starts nothing on a silent channel. A
    pitch without a note-on bends the sounding note and leaves a silent channel as it is.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Tuple[bool, Optional[str], int, int]
        channel: ChannelName = ChannelName.PULSE1
        before: ChannelPerformance
        row: Row

    test_cases: Tuple["TestApplyRow.TestCase", ...] = (
        TestCase(
            label="a sample stating no pitch starts as recorded at full volume",
            before=_silent(),
            row=Row(command=NoteOn(voice_id=SAMPLE.id)),
            expected=(True, SAMPLE.id, 0, MAX_VOLUME),
        ),
        TestCase(
            label="a sample stating a step starts at it, at the volume the row states",
            before=_silent(),
            row=Row(command=NoteOn(voice_id=SAMPLE.id), pitch=Step(value=STEP_UP), volume=LOW_VOLUME),
            expected=(True, SAMPLE.id, STEP_UP, LOW_VOLUME),
        ),
        TestCase(
            label="a sample stating a note starts at the step reaching it",
            before=_silent(),
            row=Row(command=NoteOn(voice_id=SAMPLE.id), pitch=Note(value=TYPED_NOTE)),
            expected=(True, SAMPLE.id, TYPED_NOTE - _reference(SAMPLE), MAX_VOLUME),
        ),
        TestCase(
            label="an instrument stating a note starts at the step reaching it",
            before=_silent(),
            row=Row(command=NoteOn(voice_id=LEAD.id), pitch=Note(value=TYPED_NOTE)),
            expected=(True, LEAD.id, TYPED_NOTE - _reference(LEAD), MAX_VOLUME),
        ),
        TestCase(
            label="an instrument stating a step starts at it",
            before=_silent(),
            row=Row(command=NoteOn(voice_id=LEAD.id), pitch=Step(value=STEP_DOWN)),
            expected=(True, LEAD.id, STEP_DOWN, MAX_VOLUME),
        ),
        TestCase(
            label="an instrument stating no pitch on a silent channel starts nothing",
            before=_silent(transpose=SOUNDING_STEP, volume=LOW_VOLUME),
            row=Row(command=NoteOn(voice_id=LEAD.id)),
            expected=(False, None, SOUNDING_STEP, LOW_VOLUME),
        ),
        TestCase(
            label="an instrument stating no pitch goes on from the pitch a sample was sounding",
            before=_sounding(SAMPLE.id),
            row=Row(command=NoteOn(voice_id=LEAD.id)),
            expected=(True, LEAD.id, _reference(SAMPLE) + SOUNDING_STEP - _reference(LEAD), MAX_VOLUME),
        ),
        TestCase(
            label="an instrument stating no pitch restarts the instrument already sounding",
            before=_sounding(LEAD.id),
            row=Row(command=NoteOn(voice_id=LEAD.id)),
            expected=(True, LEAD.id, SOUNDING_STEP, MAX_VOLUME),
        ),
        TestCase(
            label="a sample that has played out is still the channel's note",
            before=_sounding(SAMPLE.id, tick_index=PLAYED_OUT),
            row=Row(command=NoteOn(voice_id=LEAD.id)),
            expected=(True, LEAD.id, _reference(SAMPLE) + SOUNDING_STEP - _reference(LEAD), MAX_VOLUME),
        ),
        TestCase(
            label="a note-off leaves nothing for an instrument to go on from",
            before=_silent(transpose=SOUNDING_STEP),
            row=Row(command=NoteOn(voice_id=LEAD.id)),
            expected=(False, None, SOUNDING_STEP, MAX_VOLUME),
        ),
        TestCase(
            label="a voice silent on the channel leaves nothing to go on from",
            before=_sounding(DRUM.id),
            row=Row(command=NoteOn(voice_id=LEAD.id)),
            expected=(False, DRUM.id, SOUNDING_STEP, LOW_VOLUME),
        ),
        TestCase(
            label="a sample stating no pitch ignores what the channel was sounding",
            before=_sounding(LEAD.id),
            row=Row(command=NoteOn(voice_id=SAMPLE.id)),
            expected=(True, SAMPLE.id, 0, MAX_VOLUME),
        ),
        TestCase(
            label="noise: an instrument stating no pitch goes on from the period the channel sounds",
            channel=ChannelName.NOISE,
            before=_sounding(DRUM.id, transpose=1),
            row=Row(command=NoteOn(voice_id=LEAD.id)),
            expected=(True, LEAD.id, (DRUM_PERIOD + 1) % NUM_PERIODS - LEAD_PERIOD, MAX_VOLUME),
        ),
        TestCase(
            label="noise: a note states a period",
            channel=ChannelName.NOISE,
            before=_silent(),
            row=Row(command=NoteOn(voice_id=LEAD.id), pitch=Note(value=TYPED_PERIOD)),
            expected=(True, LEAD.id, TYPED_PERIOD - LEAD_PERIOD, MAX_VOLUME),
        ),
        TestCase(
            label="noise: a step is kept as written",
            channel=ChannelName.NOISE,
            before=_silent(),
            row=Row(command=NoteOn(voice_id=DRUM.id), pitch=Step(value=PERIOD_STEP)),
            expected=(True, DRUM.id, PERIOD_STEP, MAX_VOLUME),
        ),
        TestCase(
            label="a note-off silences the channel",
            before=_sounding(SAMPLE.id),
            row=Row(command=NoteOff()),
            expected=(True, None, SOUNDING_STEP, LOW_VOLUME),
        ),
        TestCase(
            label="a step bends the sounding sample without starting it over",
            before=_sounding(SAMPLE.id, transpose=0),
            row=Row(pitch=Step(value=STEP_DOWN), volume=QUIET_VOLUME),
            expected=(False, SAMPLE.id, STEP_DOWN, QUIET_VOLUME),
        ),
        TestCase(
            label="a note bends the sounding instrument to the step reaching it",
            before=_sounding(LEAD.id),
            row=Row(pitch=Note(value=TYPED_NOTE)),
            expected=(False, LEAD.id, TYPED_NOTE - _reference(LEAD), LOW_VOLUME),
        ),
        TestCase(
            label="a bend on a silent channel changes nothing",
            before=_silent(transpose=SOUNDING_STEP, volume=LOW_VOLUME),
            row=Row(pitch=Step(value=STEP_UP)),
            expected=(False, None, SOUNDING_STEP, LOW_VOLUME),
        ),
        TestCase(
            label="a bend on a voice the project lacks changes nothing",
            before=_sounding(GONE_ID),
            row=Row(pitch=Step(value=STEP_UP)),
            expected=(False, GONE_ID, SOUNDING_STEP, LOW_VOLUME),
        ),
        TestCase(
            label="a note-on naming a voice the project lacks starts a silent note",
            before=_sounding(SAMPLE.id),
            row=Row(command=NoteOn(voice_id=GONE_ID), pitch=Note(value=TYPED_NOTE)),
            expected=(True, GONE_ID, 0, MAX_VOLUME),
        ),
        TestCase(
            label="a volume alone sets the level of the sounding note",
            before=_sounding(SAMPLE.id),
            row=Row(volume=QUIET_VOLUME),
            expected=(False, SAMPLE.id, SOUNDING_STEP, QUIET_VOLUME),
        ),
        TestCase(
            label="an empty row leaves everything as it stands",
            before=_sounding(SAMPLE.id),
            row=Row(),
            expected=(False, SAMPLE.id, SOUNDING_STEP, LOW_VOLUME),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_what_the_channel_carries_after_the_row(self, test_case: TestCase) -> None:
        performance = deepcopy(test_case.before)

        retriggered = apply_row(performance, test_case.row, test_case.channel, LOOKUP)

        assert (retriggered, performance.voice_id, performance.transpose, performance.volume) == test_case.expected

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_tick_index_returns_to_the_start_exactly_where_the_note_does(
        self,
        test_case: TestCase,
    ) -> None:
        """A row that starts the note over is a row that starts its envelopes over."""
        performance = deepcopy(test_case.before)
        performance.tick_index = 6

        retriggered = apply_row(performance, test_case.row, test_case.channel, LOOKUP)

        assert (performance.tick_index == 0) is retriggered


class TestSoundingPitch(BaseTestSuite):
    """The pitch a channel sounds is where its voice's reference and transpose put it, and none while silent."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Optional[int]
        channel: ChannelName = ChannelName.PULSE1
        performance: ChannelPerformance

    test_cases: Tuple["TestSoundingPitch.TestCase", ...] = (
        TestCase(
            label="a silent channel sounds nothing",
            performance=_silent(transpose=SOUNDING_STEP),
            expected=None,
        ),
        TestCase(
            label="a sample sounds its reference moved by the transpose",
            performance=_sounding(SAMPLE.id),
            expected=_reference(SAMPLE) + SOUNDING_STEP,
        ),
        TestCase(
            label="a voice the project lacks sounds nothing",
            performance=_sounding(GONE_ID),
            expected=None,
        ),
        TestCase(
            label="a voice with no frames on the channel sounds nothing",
            performance=_sounding(DRUM.id),
            expected=None,
        ),
        TestCase(
            label="noise walks the step around the sixteen periods",
            channel=ChannelName.NOISE,
            performance=_sounding(DRUM.id, transpose=PERIOD_STEP),
            expected=(DRUM_PERIOD + PERIOD_STEP) % NUM_PERIODS,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_pitch_the_channel_sounds(self, test_case: TestCase) -> None:
        assert sounding_pitch(test_case.performance, test_case.channel, LOOKUP) == test_case.expected


class TestASampleHandsItsPitchToAnInstrument:
    """An instrument placed without a pitch restarts its envelopes on the pitch the sample before it reached."""

    def test_the_instrument_starts_over_on_the_samples_pitch(self) -> None:
        reading = VoiceReading.read(SAMPLE, ChannelName.PULSE1)
        assert reading is not None
        performance = ChannelPerformance(feature_values=LEFT_BEHIND.copy())
        apply_row(
            performance, Row(command=NoteOn(voice_id=SAMPLE.id), pitch=Step(value=STEP_UP)), ChannelName.PULSE1, LOOKUP
        )
        sound_tick(performance, reading)

        restarted = apply_row(performance, Row(command=NoteOn(voice_id=LEAD.id)), ChannelName.PULSE1, LOOKUP)

        assert restarted is True
        assert performance.voice_id == LEAD.id
        assert performance.transpose == _reference(SAMPLE) + STEP_UP - _reference(LEAD)
        assert performance.tick_index == 0
        assert performance.feature_values == CHANNEL_FEATURE_DEFAULTS


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
            row=Row(command=NoteOn(voice_id=SAMPLE.id)),
            expected=CHANNEL_FEATURE_DEFAULTS,
        ),
        TestCase(
            label="a note column with modifiers",
            row=Row(
                command=NoteOn(voice_id=SAMPLE.id),
                pitch=Step(value=STEP_UP),
                volume=LOW_VOLUME,
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
            row=Row(pitch=Step(value=STEP_DOWN), volume=QUIET_VOLUME),
            expected=LEFT_BEHIND,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_dimensions_the_channel_carries_after_the_row(self, test_case: TestCase) -> None:
        performance = ChannelPerformance(
            voice_id=ANOTHER.id,
            tick_index=6,
            feature_values=LEFT_BEHIND.copy(),
        )

        apply_row(performance, test_case.row, ChannelName.PULSE1, LOOKUP)

        assert performance.feature_values == test_case.expected

    def test_a_note_leaves_the_defaults_themselves_untouched(self) -> None:
        """Each note takes a copy, so what a note writes reaches neither the next nor a song's start."""
        defaults = dict(CHANNEL_FEATURE_DEFAULTS)
        performance = ChannelPerformance(voice_id=ANOTHER.id)
        apply_row(performance, Row(command=NoteOn(voice_id=SAMPLE.id)), ChannelName.PULSE1, LOOKUP)

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
        lookup: VoiceLookup = {writes.id: writes, holds.id: holds}.get
        writes_reading = VoiceReading.read(writes, ChannelName.PULSE1)
        holds_reading = VoiceReading.read(holds, ChannelName.PULSE1)
        assert writes_reading is not None and holds_reading is not None

        performance = ChannelPerformance()
        apply_row(performance, Row(command=NoteOn(voice_id=writes.id)), ChannelName.PULSE1, lookup)
        sound_tick(performance, writes_reading)
        apply_row(performance, Row(command=NoteOn(voice_id=holds.id)), ChannelName.PULSE1, lookup)
        sounded = sound_tick(performance, holds_reading)

        assert sounded is not None and sounded.on is True
        assert performance.feature_values[FeatureKey.VOLUME] == MAX_VOLUME
