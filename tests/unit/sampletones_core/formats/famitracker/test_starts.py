from dataclasses import dataclass
from typing import Dict, Final, List, Mapping, Optional, Sequence, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.skipped import BuiltDocument, SkippedRow, SkipReason
from sampletones_core.formats.famitracker.builder import build_instrument_table, build_module
from sampletones_core.formats.famitracker.model.module import FamiTrackerModule
from sampletones_core.formats.famitracker.model.pattern import RowCell
from sampletones_core.project.patterns.pitch import Step
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceUnion, voice_reference
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.famitracker import cell_pitch, module_cell, replayed_pitches
from tests.suite.transposes import (
    contour_sample,
    flat_instrument,
    note,
    one_channel_project,
    rows_with,
    sounded_pitches,
)

SETTINGS: Final[ProjectSettings] = ProjectSettings()
CHANNEL: Final[ChannelName] = ChannelName.PULSE1
FRAMES: Final[int] = 240
ORGAN_PITCH: Final[int] = 72
ORGAN_PERIOD: Final[int] = 6
NOTE_TRANSPOSE: Final[int] = 5
RAISED: Final[int] = 2
LOWERED: Final[int] = -3
BEND_ROW: Final[int] = 2
NOTE_OFF_ROW: Final[int] = 3
INSTRUMENT_ROW: Final[int] = 6
LATER_BEND_ROW: Final[int] = 9
LATER_NOTE_OFF_ROW: Final[int] = 11
SILENT_INSTRUMENT_ROW: Final[int] = 13
SHARED_PATTERN: Final[int] = 2
DECIDING_ORDER: Final[Tuple[Optional[int], ...]] = (0, SHARED_PATTERN, 1, SHARED_PATTERN)
AGREEING_ORDER: Final[Tuple[Optional[int], ...]] = (0, SHARED_PATTERN, SHARED_PATTERN)
REPORTED_FRAME: Final[int] = 3


def organ_for(channel_name: ChannelName) -> Instrument:
    return flat_instrument(channel_name, ORGAN_PERIOD if channel_name == ChannelName.NOISE else ORGAN_PITCH)


@pytest.fixture(name="lead")
def lead_fixture() -> Sample:
    return contour_sample(CHANNEL, FRAMES)


@pytest.fixture(name="organ")
def organ_fixture() -> Instrument:
    return organ_for(CHANNEL)


def arranged(
    voices: Sequence[VoiceUnion],
    patterns: Mapping[int, List[Row]],
    order: Sequence[Optional[int]],
    channel_name: ChannelName = CHANNEL,
) -> Project:
    return one_channel_project(voices, channel_name, patterns, order, settings=SETTINGS)


def built(
    voices: Sequence[VoiceUnion],
    patterns: Mapping[int, List[Row]],
    order: Sequence[Optional[int]],
) -> BuiltDocument[FamiTrackerModule]:
    return build_module(arranged(voices, patterns, order))


def instrument_cell(document: FamiTrackerModule, pattern_index: int) -> RowCell:
    cell = module_cell(document, CHANNEL, pattern_index, INSTRUMENT_ROW)
    assert cell is not None
    return cell


def reported(organ: Instrument, order_position: int) -> SkippedRow:
    return SkippedRow(
        voice_id=organ.id,
        channel=CHANNEL,
        order_position=order_position,
        row_index=INSTRUMENT_ROW,
        reason=SkipReason.CARRIED_PITCH,
    )


class TestAnInstrumentPlacedWithoutAPitch:
    """The song starts such an instrument on the pitch the channel is sounding, whichever voice sounded
    it, and leaves a silent channel silent, so the cell writes that note beside the instrument where
    the song sounds one and stays empty where it sounds none.
    """

    def test_the_cell_writes_the_note_the_sample_was_sounding(self, lead: Sample, organ: Instrument) -> None:
        project = arranged(
            (lead, organ),
            {0: rows_with((0, note(lead, NOTE_TRANSPOSE)), (INSTRUMENT_ROW, note(organ)))},
            [0],
        )
        _, slots = build_instrument_table(project)

        cell = instrument_cell(build_module(project).document, 0)

        assert cell_pitch(cell) == voice_reference(lead, CHANNEL) + NOTE_TRANSPOSE
        assert cell.instrument == slots[(organ.id, CHANNEL)].index

    def test_the_note_follows_a_bend(self, lead: Sample, organ: Instrument) -> None:
        document = built(
            (lead, organ),
            {0: rows_with((0, note(lead)), (BEND_ROW, Row(pitch=Step(value=RAISED))), (INSTRUMENT_ROW, note(organ)))},
            [0],
        ).document

        assert cell_pitch(instrument_cell(document, 0)) == voice_reference(lead, CHANNEL) + RAISED

    def test_a_silent_channel_leaves_the_cell_empty(self, organ: Instrument) -> None:
        built_module = built((organ,), {0: rows_with((INSTRUMENT_ROW, note(organ)))}, [0])

        assert module_cell(built_module.document, CHANNEL, 0, INSTRUMENT_ROW) is None
        assert built_module.skipped_rows == ()

    def test_a_note_off_before_it_leaves_the_cell_empty(self, lead: Sample, organ: Instrument) -> None:
        document = built(
            (lead, organ),
            {0: rows_with((0, note(lead)), (NOTE_OFF_ROW, Row(command=NoteOff())), (INSTRUMENT_ROW, note(organ)))},
            [0],
        ).document

        assert module_cell(document, CHANNEL, 0, INSTRUMENT_ROW) is None


class TestACellSeveralFramesReach:
    """A module stores a pattern once for every frame that plays it, so the first frame reaching an
    instrument's cell decides its note, and a later frame reaching it after another pitch, or silent,
    is reported.
    """

    def test_the_first_frame_decides_the_note(self, lead: Sample, organ: Instrument) -> None:
        document = built(
            (lead, organ),
            {
                0: rows_with((0, note(lead, RAISED))),
                1: rows_with((0, note(lead, LOWERED))),
                SHARED_PATTERN: rows_with((INSTRUMENT_ROW, note(organ))),
            },
            DECIDING_ORDER,
        ).document

        assert cell_pitch(instrument_cell(document, SHARED_PATTERN)) == voice_reference(lead, CHANNEL) + RAISED

    def test_a_frame_reaching_the_cell_after_another_pitch_is_reported(self, lead: Sample, organ: Instrument) -> None:
        built_module = built(
            (lead, organ),
            {
                0: rows_with((0, note(lead, RAISED))),
                1: rows_with((0, note(lead, LOWERED))),
                SHARED_PATTERN: rows_with((INSTRUMENT_ROW, note(organ))),
            },
            DECIDING_ORDER,
        )

        assert built_module.skipped_rows == (reported(organ, REPORTED_FRAME),)

    def test_a_frame_reaching_the_cell_silent_is_reported(self, lead: Sample, organ: Instrument) -> None:
        built_module = built(
            (lead, organ),
            {
                0: rows_with((0, note(lead))),
                1: rows_with((0, Row(command=NoteOff()))),
                SHARED_PATTERN: rows_with((INSTRUMENT_ROW, note(organ))),
            },
            DECIDING_ORDER,
        )

        assert cell_pitch(instrument_cell(built_module.document, SHARED_PATTERN)) == voice_reference(lead, CHANNEL)
        assert built_module.skipped_rows == (reported(organ, REPORTED_FRAME),)

    def test_frames_reaching_the_cell_at_one_pitch_report_nothing(self, lead: Sample, organ: Instrument) -> None:
        """The instrument the first frame started goes on sounding into the second, so the second frame
        starts it at the pitch it already sounds.
        """
        built_module = built(
            (lead, organ),
            {0: rows_with((0, note(lead, RAISED))), SHARED_PATTERN: rows_with((INSTRUMENT_ROW, note(organ)))},
            AGREEING_ORDER,
        )

        assert built_module.skipped_rows == ()


class TestAnInstrumentTakingTheChannelsPitchSoundsTheSongsPitch(BaseTestSuite):
    """Played the way FamiTracker reads its rows, an instrument that takes the pitch a sample left, is
    bent afterwards, and is placed again on a silent channel sounds the pitch the song's walk sounds on
    every tick the song sounds.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        channel: ChannelName

    test_cases: Tuple["TestAnInstrumentTakingTheChannelsPitchSoundsTheSongsPitch.TestCase", ...] = (
        TestCase(label="pulse", channel=ChannelName.PULSE1),
        TestCase(label="triangle", channel=ChannelName.TRIANGLE),
        TestCase(label="noise", channel=ChannelName.NOISE),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_every_sounding_tick_plays_the_songs_pitch(
        self,
        test_case: "TestAnInstrumentTakingTheChannelsPitchSoundsTheSongsPitch.TestCase",
    ) -> None:
        lead = contour_sample(test_case.channel, FRAMES)
        organ = organ_for(test_case.channel)
        patterns: Dict[int, List[Row]] = {
            0: rows_with(
                (0, note(lead, NOTE_TRANSPOSE)),
                (BEND_ROW, Row(pitch=Step(value=RAISED))),
                (INSTRUMENT_ROW, note(organ)),
                (LATER_BEND_ROW, Row(pitch=Step(value=LOWERED))),
                (LATER_NOTE_OFF_ROW, Row(command=NoteOff())),
                (SILENT_INSTRUMENT_ROW, note(organ)),
            ),
        }
        project = arranged((lead, organ), patterns, [0], test_case.channel)

        sounded = sounded_pitches(project, test_case.channel)
        played = replayed_pitches(build_module(project).document, project, test_case.channel)

        assert len(played) == len(sounded)
        assert [tick for tick, pitch in enumerate(sounded) if pitch is not None and played[tick] != pitch] == []
        assert played[-1] is None
