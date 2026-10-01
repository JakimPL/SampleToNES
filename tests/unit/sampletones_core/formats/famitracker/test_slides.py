from dataclasses import dataclass
from typing import Final, List, Optional, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PERIOD, MAX_PITCH, MIN_PLAYED_PITCH, NUM_PERIODS
from sampletones_core.exporters.skipped import BuiltDocument, SkippedRow, SkipReason
from sampletones_core.formats.famitracker.builder import build_module
from sampletones_core.formats.famitracker.model.instrument import Instrument2A03
from sampletones_core.formats.famitracker.model.module import FamiTrackerModule
from sampletones_core.formats.famitracker.model.pattern import RowCell
from sampletones_core.formats.famitracker.module import module_to_ftm_bytes
from sampletones_core.formats.famitracker.slides import slide_effect
from sampletones_core.formats.famitracker.specification.channels import CHANNEL_TO_ID
from sampletones_core.formats.famitracker.specification.patterns import (
    EMPTY_EFFECT,
    EMPTY_INSTRUMENT,
    EMPTY_NOTE,
    FASTEST_SLIDE_SPEED,
    MAX_SLIDE_SEMITONES,
    SLIDE_SPEED_SHIFT,
    EffectId,
)
from sampletones_core.formats.famitracker.specification.sequences import NO_LOOP_POINT, SequenceKind
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.project.voices.sample import Sample
from sampletones_core.timing.bounds import SONG_TICK_BOUNDS
from sampletones_core.timing.song import SongTiming
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.famitracker import parse_ftm, played_notes
from tests.suite.transposes import (
    contour_sample,
    flat_sample,
    note,
    one_channel_project,
    rows_with,
    settling_sample,
    sounded_pitches,
)

UNIFORM_SETTINGS: Final[ProjectSettings] = ProjectSettings()
GROOVE_SETTINGS: Final[ProjectSettings] = ProjectSettings(tempo=210)
CHANNEL: Final[ChannelName] = ChannelName.PULSE1
FRAMES: Final[int] = 240
FLAT_FRAMES: Final[int] = 8
FLAT_PITCH: Final[int] = 40
HIGH_PITCH: Final[int] = 115
RAISED: Final[int] = 2
LOWERED: Final[int] = -3
NOTE_TRANSPOSE: Final[int] = 5
RESTARTED_TRANSPOSE: Final[int] = 4
AFTER_RESET_TRANSPOSE: Final[int] = 1
RAISED_ROW: Final[int] = 3
LOWERED_ROW: Final[int] = 7
RESET_ROW: Final[int] = 10
AFTER_RESET_ROW: Final[int] = 13
LATE_NOTE_ROW: Final[int] = 12
FAR_TRANSPOSE: Final[int] = MAX_SLIDE_SEMITONES + 5
LOW_FLAT_PITCH: Final[int] = 36
SUBMERGED_TRANSPOSE: Final[int] = -14
SOARING_TRANSPOSE: Final[int] = 10
NOISE_PERIOD: Final[int] = 3
NOISE_TRANSPOSES: Final[Tuple[int, ...]] = (-5, 12, 40)
PITCH_OFFSET: Final[int] = 24
SHORT_ORDER: Final[Tuple[Optional[int], ...]] = (0, 1, 2)


def cell(
    document: FamiTrackerModule,
    pattern_index: int,
    row_number: int,
    channel: ChannelName = CHANNEL,
) -> Optional[RowCell]:
    """The cell a pattern stores at a row, or ``None`` where the row is empty."""
    channel_id = CHANNEL_TO_ID[channel]
    for pattern in document.track.patterns:
        if pattern.channel == channel_id and pattern.index == pattern_index:
            return next((row for row in pattern.rows if row.row_number == row_number), None)

    return None


def slide_at(
    document: FamiTrackerModule,
    pattern_index: int,
    row_number: int,
    channel: ChannelName = CHANNEL,
) -> Optional[Tuple[int, int]]:
    """The note slide a cell's first effect column writes, or ``None`` where it writes none."""
    row = cell(document, pattern_index, row_number, channel)
    if row is None or row.effects[0][0] == EMPTY_EFFECT:
        return None

    return row.effects[0]


def semitones_up(semitones: int) -> Tuple[int, int]:
    return int(EffectId.SLIDE_UP), (FASTEST_SLIDE_SPEED << SLIDE_SPEED_SHIFT) | semitones


def semitones_down(semitones: int) -> Tuple[int, int]:
    return int(EffectId.SLIDE_DOWN), (FASTEST_SLIDE_SPEED << SLIDE_SPEED_SHIFT) | semitones


def instrument_of(document: FamiTrackerModule, index: int) -> Instrument2A03:
    return next(instrument for instrument in document.instruments if instrument.index == index)


@pytest.fixture(name="lead")
def lead_fixture() -> Sample:
    return contour_sample(CHANNEL, FRAMES)


def slid(voice: Sample, *cells: Tuple[int, Row]) -> BuiltDocument[FamiTrackerModule]:
    return build_module(one_channel_project((voice,), CHANNEL, {0: rows_with(*cells)}, [0], settings=UNIFORM_SETTINGS))


class TestTheSlideATransposeRowWrites:
    """``Qxy`` and ``Rxy`` move the channel's note by ``y`` semitones, so a transpose row writes the slide
    from the note the channel holds to the note a note-on at the row's transpose would write, at the
    highest speed.
    """

    def test_the_encoding_names_the_direction_the_speed_and_the_semitones(self) -> None:
        """The effect number and its parameter are the file format's own, which is the contract here."""
        assert slide_effect(RAISED) == (int(EffectId.SLIDE_UP), 0xF0 | RAISED)
        assert slide_effect(LOWERED) == (int(EffectId.SLIDE_DOWN), 0xF0 | -LOWERED)

    def test_a_rise_slides_the_note_up(self, lead: Sample) -> None:
        document = slid(lead, (0, note(lead)), (RAISED_ROW, Row(transpose=RAISED))).document

        assert slide_at(document, 0, RAISED_ROW) == semitones_up(RAISED)

    def test_the_row_leaves_the_note_and_the_instrument_alone(self, lead: Sample) -> None:
        """A note or an instrument cell retriggers the instrument, so the row writes neither."""
        document = slid(lead, (0, note(lead)), (RAISED_ROW, Row(transpose=RAISED))).document
        row = cell(document, 0, RAISED_ROW)

        assert row is not None
        assert (row.note, row.instrument) == (EMPTY_NOTE, EMPTY_INSTRUMENT)

    def test_a_second_row_slides_from_where_the_first_left_the_note(self, lead: Sample) -> None:
        document = slid(
            lead,
            (0, note(lead)),
            (RAISED_ROW, Row(transpose=RAISED)),
            (LOWERED_ROW, Row(transpose=LOWERED)),
        ).document

        assert slide_at(document, 0, LOWERED_ROW) == semitones_down(RAISED - LOWERED)

    def test_the_slide_counts_from_the_transpose_the_note_started_at(self, lead: Sample) -> None:
        document = slid(lead, (0, note(lead, NOTE_TRANSPOSE)), (RAISED_ROW, Row(transpose=RAISED))).document

        assert slide_at(document, 0, RAISED_ROW) == semitones_down(NOTE_TRANSPOSE - RAISED)

    def test_a_note_on_starts_the_slides_over(self, lead: Sample) -> None:
        document = slid(
            lead,
            (0, note(lead)),
            (RAISED_ROW, Row(transpose=RAISED)),
            (RESET_ROW, note(lead, RESTARTED_TRANSPOSE)),
            (AFTER_RESET_ROW, Row(transpose=AFTER_RESET_TRANSPOSE)),
        ).document

        assert slide_at(document, 0, RESET_ROW) is None
        assert slide_at(document, 0, AFTER_RESET_ROW) == semitones_down(RESTARTED_TRANSPOSE - AFTER_RESET_TRANSPOSE)

    def test_a_row_restating_the_transpose_in_force_writes_no_slide(self, lead: Sample) -> None:
        document = slid(
            lead,
            (0, note(lead)),
            (RAISED_ROW, Row(transpose=RAISED)),
            (LOWERED_ROW, Row(transpose=RAISED)),
        ).document

        assert slide_at(document, 0, LOWERED_ROW) is None

    def test_a_transpose_below_the_range_slides_to_the_lowest_pitch(self) -> None:
        """A note-on at the new transpose writes its note by the low-pitch rule, so a flat instrument
        slides to C-0, the lowest pitch the song plays.
        """
        flat = flat_sample(CHANNEL, LOW_FLAT_PITCH, FLAT_FRAMES)
        document = slid(flat, (0, note(flat)), (RAISED_ROW, Row(transpose=SUBMERGED_TRANSPOSE))).document

        assert slide_at(document, 0, RAISED_ROW) == semitones_down(LOW_FLAT_PITCH - MIN_PLAYED_PITCH)

    def test_a_transpose_above_the_range_slides_to_the_highest_pitch(self) -> None:
        high = flat_sample(CHANNEL, HIGH_PITCH, FLAT_FRAMES)
        document = slid(high, (0, note(high)), (RAISED_ROW, Row(transpose=SOARING_TRANSPOSE))).document

        assert slide_at(document, 0, RAISED_ROW) == semitones_up(MAX_PITCH - HIGH_PITCH)

    def test_a_slide_is_the_same_however_long_the_note_has_sounded(self, lead: Sample) -> None:
        """The slide moves the note, which a running arpeggio reads on every tick, so neither the groove
        nor the frames between the note and the row change what the row writes.
        """
        project = one_channel_project(
            (lead,),
            CHANNEL,
            {0: rows_with((LATE_NOTE_ROW, note(lead))), 1: rows_with((RAISED_ROW, Row(transpose=RAISED)))},
            [0, None, 1],
            settings=GROOVE_SETTINGS,
        )

        assert slide_at(build_module(project).document, 1, RAISED_ROW) == semitones_up(RAISED)


class TestTheSlidesAModuleCannotCarry:
    """A slide reaches fifteen semitones, and a module stores a pattern once for every frame that plays
    it, so a row moving the note further or a shared cell needing different slides is written without
    one there and reported. The rows after it slide from the note the channel holds.
    """

    def test_a_row_moving_the_note_past_a_slide_is_reported(self, lead: Sample) -> None:
        built = slid(lead, (0, note(lead)), (RAISED_ROW, Row(transpose=FAR_TRANSPOSE)))

        assert slide_at(built.document, 0, RAISED_ROW) is None
        assert built.skipped_rows == (
            SkippedRow(
                voice_id=lead.id,
                channel=CHANNEL,
                order_position=0,
                row_index=RAISED_ROW,
                reason=SkipReason.UNREACHED_TRANSPOSE,
            ),
        )

    def test_the_row_after_it_slides_from_the_note_the_channel_holds(self, lead: Sample) -> None:
        built = slid(
            lead,
            (0, note(lead)),
            (RAISED_ROW, Row(transpose=FAR_TRANSPOSE)),
            (LOWERED_ROW, Row(transpose=RAISED)),
        )

        assert slide_at(built.document, 0, LOWERED_ROW) == semitones_up(RAISED)

    def test_a_shared_cell_needing_another_slide_in_a_later_frame_is_reported(self, lead: Sample) -> None:
        """The pattern holding the transpose row plays after notes at two transposes, so the slide the
        first frame decides moves the second frame's note elsewhere.
        """
        project = one_channel_project(
            (lead,),
            CHANNEL,
            {
                0: rows_with((0, note(lead))),
                1: rows_with((RAISED_ROW, Row(transpose=RAISED))),
                2: rows_with((0, note(lead, NOTE_TRANSPOSE))),
            },
            [0, 1, 2, 1],
            settings=UNIFORM_SETTINGS,
        )
        built = build_module(project)

        assert slide_at(built.document, 1, RAISED_ROW) == semitones_up(RAISED)
        assert built.skipped_rows == (
            SkippedRow(
                voice_id=lead.id,
                channel=CHANNEL,
                order_position=3,
                row_index=RAISED_ROW,
                reason=SkipReason.UNREACHED_TRANSPOSE,
            ),
        )

    @pytest.mark.parametrize("transpose", NOISE_TRANSPOSES)
    def test_every_noise_slide_is_within_reach(self, transpose: int) -> None:
        """The note on noise is the period, and both notes lie within the sixteen periods, so a slide
        between them reaches every transpose and the channel lands on the period the transpose walks to.
        """
        drum = flat_sample(ChannelName.NOISE, NOISE_PERIOD, FLAT_FRAMES)
        project = one_channel_project(
            (drum,),
            ChannelName.NOISE,
            {0: rows_with((0, note(drum)), (RAISED_ROW, Row(transpose=transpose)))},
            [0],
            settings=UNIFORM_SETTINGS,
        )
        built = build_module(project)
        effect = slide_at(built.document, 0, RAISED_ROW, ChannelName.NOISE)

        assert built.skipped_rows == ()
        assert effect is not None
        direction = 1 if effect[0] == int(EffectId.SLIDE_UP) else -1
        moved = NOISE_PERIOD + direction * (effect[1] & MAX_SLIDE_SEMITONES)
        assert moved == (NOISE_PERIOD + transpose) % NUM_PERIODS


class TestTheInstrumentsASlideReaches:
    """Only an arpeggio still running reloads the period from the note a slide moved, so an instrument a
    slide reaches keeps its arpeggio running, and a module without a slide keeps every instrument as it
    was.
    """

    def test_the_arpeggio_of_an_instrument_a_slide_reaches_keeps_running(self, lead: Sample) -> None:
        document = slid(lead, (0, note(lead)), (RAISED_ROW, Row(transpose=RAISED))).document
        arpeggio = instrument_of(document, 0).sequences[SequenceKind.ARPEGGIO]

        assert arpeggio.loop_point == len(arpeggio.items) - 1

    def test_an_instrument_no_slide_reaches_is_left_as_it_was(self, lead: Sample) -> None:
        document = slid(lead, (0, note(lead)), (RAISED_ROW, Row(transpose=0))).document
        arpeggio = instrument_of(document, 0).sequences[SequenceKind.ARPEGGIO]

        assert arpeggio.loop_point == NO_LOOP_POINT


def replayed(document: FamiTrackerModule, project: Project, channel_name: ChannelName) -> List[Optional[int]]:
    """What FamiTracker sounds on one channel each tick: the pitch, or on noise the period register."""
    notes = played_notes(
        parse_ftm(module_to_ftm_bytes(document)),
        int(CHANNEL_TO_ID[channel_name]),
        SongTiming.from_project(project, bounds=SONG_TICK_BOUNDS),
    )
    if channel_name == ChannelName.NOISE:
        return [None if value is None else MAX_PERIOD - value for value in notes]

    return [None if value is None else value + PITCH_OFFSET for value in notes]


class TestATransposedSongSoundsTheSongsPitch(BaseTestSuite):
    """Played the way FamiTracker reads its rows, a song whose transpose rows move a sounding note, cross
    frames under a groove, and meet a note-on starting over sounds the pitch the song's walk sounds on
    every tick the song sounds.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        channel: ChannelName
        settling: bool

    test_cases: Tuple["TestATransposedSongSoundsTheSongsPitch.TestCase", ...] = (
        TestCase(label="pulse", channel=ChannelName.PULSE1, settling=False),
        TestCase(label="triangle", channel=ChannelName.TRIANGLE, settling=False),
        TestCase(label="noise", channel=ChannelName.NOISE, settling=False),
        TestCase(label="pulse_settling", channel=ChannelName.PULSE1, settling=True),
        TestCase(label="triangle_settling", channel=ChannelName.TRIANGLE, settling=True),
        TestCase(label="noise_settling", channel=ChannelName.NOISE, settling=True),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_every_sounding_tick_plays_the_songs_pitch(
        self,
        test_case: "TestATransposedSongSoundsTheSongsPitch.TestCase",
    ) -> None:
        """A settling voice's arpeggio has played its items before the first transpose row comes."""
        voice = (
            settling_sample(test_case.channel, FRAMES)
            if test_case.settling
            else contour_sample(test_case.channel, FRAMES)
        )
        patterns = {
            0: rows_with((0, note(voice)), (RAISED_ROW, Row(transpose=RAISED))),
            1: rows_with(
                (2, Row(transpose=LOWERED)),
                (RESET_ROW, note(voice)),
                (AFTER_RESET_ROW, Row(transpose=AFTER_RESET_TRANSPOSE)),
            ),
            2: rows_with((RAISED_ROW, Row(transpose=LOWERED)), (LOWERED_ROW, Row(transpose=0))),
        }
        project = one_channel_project(
            (voice,),
            test_case.channel,
            patterns,
            list(SHORT_ORDER),
            settings=GROOVE_SETTINGS,
        )

        sounded = sounded_pitches(project, test_case.channel)
        played = replayed(build_module(project).document, project, test_case.channel)

        assert len(played) == len(sounded)
        assert [tick for tick, pitch in enumerate(sounded) if pitch is not None and played[tick] != pitch] == []
