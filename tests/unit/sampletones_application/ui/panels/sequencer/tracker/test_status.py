from dataclasses import dataclass
from typing import Dict, Final, FrozenSet, Optional, Tuple

import pytest

from sampletones_application.categories.elements.sequencer import SequencerTrackerElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.ui.panels.sequencer.tracker.status import CellStatusText
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.tracker import (
    SequencerCellViewModel,
    SequencerRowViewModel,
)
from sampletones_application.view_model.sequencer.voices import VoiceEntryViewModel, VoiceKind
from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.patterns.pitch import Note, RowPitch, Step
from sampletones_core.project.patterns.row import NoteCommand
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.utils.display import display_id, display_pitch, display_volume
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.language import FakeLanguageManager

KICK: Final[VoiceEntryViewModel] = VoiceEntryViewModel(voice_id="kick-id", name="Kick", kind=VoiceKind.SAMPLE)
LEAD: Final[VoiceEntryViewModel] = VoiceEntryViewModel(voice_id="lead-id", name="Lead", kind=VoiceKind.INSTRUMENT)
VOICES: Final[Tuple[VoiceEntryViewModel, ...]] = (KICK, LEAD)
GONE: Final[str] = "gone-id"
NO_CHANNELS: Final[FrozenSet[ChannelName]] = frozenset()
BOTH: Final[FrozenSet[ChannelName]] = frozenset({ChannelName.PULSE1, ChannelName.TRIANGLE})
MIDDLE_C: Final[int] = 60
PERIOD: Final[int] = 4
LEVEL: Final[int] = 13
TEXTS: Final[Dict[object, str]] = {
    (Page.SEQUENCER, Panel.TRACKER, TextType.LABEL, SequencerTrackerElements.STATUS_VOICE): "Voice",
    (Page.SEQUENCER, Panel.TRACKER, TextType.LABEL, SequencerTrackerElements.STATUS_SAMPLE): "Sample",
    (Page.SEQUENCER, Panel.TRACKER, TextType.LABEL, SequencerTrackerElements.STATUS_PITCH): "Pitch",
    (Page.SEQUENCER, Panel.TRACKER, TextType.LABEL, SequencerTrackerElements.STATUS_VOLUME): "Volume",
    (Page.SEQUENCER, Panel.TRACKER, TextType.LABEL, SequencerTrackerElements.STATUS_NOTE_OFF): "Note off",
    (
        Page.SEQUENCER,
        Panel.TRACKER,
        TextType.LABEL,
        SequencerTrackerElements.STATUS_DIFFERENT_VOICES,
    ): "Different voices",
    (
        Page.SEQUENCER,
        Panel.TRACKER,
        TextType.LABEL,
        SequencerTrackerElements.STATUS_DIFFERENT_PITCHES,
    ): "Different pitches",
    (
        Page.SEQUENCER,
        Panel.TRACKER,
        TextType.LABEL,
        SequencerTrackerElements.STATUS_DIFFERENT_VOLUMES,
    ): "Different volumes",
    "sequencer.tracker.template.status_voice": "Voice {voice}",
    "sequencer.tracker.template.status_sample": "Sample {voice}",
    "sequencer.tracker.template.status_note": "Note {note}",
    "sequencer.tracker.template.status_period": "Period {period}",
    "sequencer.tracker.template.status_transpose": "Transpose {step}",
    "sequencer.tracker.template.status_volume": "Volume {volume}",
}


def _cell(
    command: Optional[NoteCommand] = None,
    pitch: Optional[RowPitch] = None,
    level: Optional[int] = None,
    kind: Optional[VoiceKind] = None,
) -> SequencerCellViewModel:
    return SequencerCellViewModel(
        voice=display_id(None),
        transpose=display_pitch(pitch),
        volume=display_volume(level),
        kind=kind,
        pitch=pitch,
        level=level,
        command=command,
    )


def _row(
    cells: Dict[ChannelName, SequencerCellViewModel],
    sample_channels: FrozenSet[ChannelName] = NO_CHANNELS,
    carried_channels: FrozenSet[ChannelName] = NO_CHANNELS,
) -> SequencerRowViewModel:
    """A row holding ``cells`` on the channels named and empty cells on the rest."""
    return SequencerRowViewModel(
        index=0,
        cells={channel: cells.get(channel, _cell()) for channel in ChannelName.items()},
        sample_channels=sample_channels,
        carried_channels=carried_channels,
    )


def _kick() -> SequencerCellViewModel:
    return _cell(command=NoteOn(voice_id=KICK.voice_id), kind=VoiceKind.SAMPLE)


def _lead() -> SequencerCellViewModel:
    return _cell(command=NoteOn(voice_id=LEAD.voice_id), kind=VoiceKind.INSTRUMENT)


@pytest.fixture(name="status")
def status_fixture() -> CellStatusText:
    return CellStatusText(FakeLanguageManager(texts=TEXTS))


class TestWhatTheStatusSaysOfASlot(BaseTestSuite):
    """A slot is named by what it holds in the terms the grid prints it in, and an empty one by its name."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        row: SequencerRowViewModel
        channel: Optional[ChannelName]
        subcolumn: SubColumn
        expected: str

    test_cases: Tuple["TestWhatTheStatusSaysOfASlot.TestCase", ...] = (
        TestCase(
            label="a voice by its number and name",
            row=_row({ChannelName.PULSE1: _lead()}),
            channel=ChannelName.PULSE1,
            subcolumn=SubColumn.VOICE,
            expected="Voice 01: Lead",
        ),
        TestCase(
            label="a cut",
            row=_row({ChannelName.PULSE1: _cell(command=NoteOff())}),
            channel=ChannelName.PULSE1,
            subcolumn=SubColumn.VOICE,
            expected="Note off",
        ),
        TestCase(
            label="an empty voice slot",
            row=_row({}),
            channel=ChannelName.PULSE1,
            subcolumn=SubColumn.VOICE,
            expected="Voice",
        ),
        TestCase(
            label="a voice the pool lacks",
            row=_row({ChannelName.PULSE1: _cell(command=NoteOn(voice_id=GONE))}),
            channel=ChannelName.PULSE1,
            subcolumn=SubColumn.VOICE,
            expected="Voice",
        ),
        TestCase(
            label="a note by its name",
            row=_row({ChannelName.PULSE1: _cell(pitch=Note(value=MIDDLE_C))}),
            channel=ChannelName.PULSE1,
            subcolumn=SubColumn.TRANSPOSE,
            expected=f"Note {display_pitch(Note(value=MIDDLE_C))}",
        ),
        TestCase(
            label="a period by its number",
            row=_row({ChannelName.NOISE: _cell(pitch=Note(value=PERIOD))}),
            channel=ChannelName.NOISE,
            subcolumn=SubColumn.TRANSPOSE,
            expected=f"Period {PERIOD}",
        ),
        TestCase(
            label="a step up in decimal",
            row=_row({ChannelName.PULSE1: _cell(pitch=Step(value=3))}),
            channel=ChannelName.PULSE1,
            subcolumn=SubColumn.TRANSPOSE,
            expected="Transpose +3",
        ),
        TestCase(
            label="a step down in decimal",
            row=_row({ChannelName.PULSE1: _cell(pitch=Step(value=-12))}),
            channel=ChannelName.PULSE1,
            subcolumn=SubColumn.TRANSPOSE,
            expected="Transpose -12",
        ),
        TestCase(
            label="an empty pitch slot",
            row=_row({}),
            channel=ChannelName.PULSE1,
            subcolumn=SubColumn.TRANSPOSE,
            expected="Pitch",
        ),
        TestCase(
            label="a volume by its level",
            row=_row({ChannelName.PULSE1: _cell(level=LEVEL)}),
            channel=ChannelName.PULSE1,
            subcolumn=SubColumn.VOLUME,
            expected=f"Volume {LEVEL}",
        ),
        TestCase(
            label="an empty volume slot",
            row=_row({}),
            channel=ChannelName.PULSE1,
            subcolumn=SubColumn.VOLUME,
            expected="Volume",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_sentence(self, status: CellStatusText, test_case: TestCase) -> None:
        assert status.describe(test_case.row, test_case.channel, test_case.subcolumn, VOICES) == test_case.expected


class TestWhatTheStatusSaysOfTheSampleColumn(BaseTestSuite):
    """The sample column's slot speaks for the channels its row spans, and says when they differ."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        row: SequencerRowViewModel
        subcolumn: SubColumn
        expected: str

    test_cases: Tuple["TestWhatTheStatusSaysOfTheSampleColumn.TestCase", ...] = (
        TestCase(
            label="a sample over its channels",
            row=_row({ChannelName.PULSE1: _kick(), ChannelName.TRIANGLE: _kick()}, sample_channels=BOTH),
            subcolumn=SubColumn.VOICE,
            expected="Sample 00: Kick",
        ),
        TestCase(
            label="a sample missing from one of its channels",
            row=_row({ChannelName.PULSE1: _kick(), ChannelName.TRIANGLE: _lead()}, sample_channels=BOTH),
            subcolumn=SubColumn.VOICE,
            expected="Different voices",
        ),
        TestCase(
            label="an instrument alone reads as an empty sample slot",
            row=_row({ChannelName.PULSE1: _lead()}),
            subcolumn=SubColumn.VOICE,
            expected="Sample",
        ),
        TestCase(
            label="a row cut everywhere",
            row=_row({channel: _cell(command=NoteOff()) for channel in ChannelName.items()}),
            subcolumn=SubColumn.VOICE,
            expected="Note off",
        ),
        TestCase(
            label="pitches that differ",
            row=_row(
                {
                    ChannelName.PULSE1: _cell(pitch=Note(value=MIDDLE_C)),
                    ChannelName.TRIANGLE: _cell(pitch=Step(value=3)),
                },
                sample_channels=BOTH,
            ),
            subcolumn=SubColumn.TRANSPOSE,
            expected="Different pitches",
        ),
        TestCase(
            label="pitches that agree",
            row=_row(
                {ChannelName.PULSE1: _cell(pitch=Step(value=3)), ChannelName.TRIANGLE: _cell(pitch=Step(value=3))},
                carried_channels=BOTH,
            ),
            subcolumn=SubColumn.TRANSPOSE,
            expected="Transpose +3",
        ),
        TestCase(
            label="a pitch slot spanning no channel",
            row=_row({ChannelName.PULSE1: _cell(pitch=Step(value=3))}),
            subcolumn=SubColumn.TRANSPOSE,
            expected="Pitch",
        ),
        TestCase(
            label="volumes that differ",
            row=_row(
                {ChannelName.PULSE1: _cell(level=LEVEL), ChannelName.TRIANGLE: _cell(level=LEVEL - 1)},
                sample_channels=BOTH,
            ),
            subcolumn=SubColumn.VOLUME,
            expected="Different volumes",
        ),
        TestCase(
            label="volumes that agree",
            row=_row(
                {ChannelName.PULSE1: _cell(level=LEVEL), ChannelName.TRIANGLE: _cell(level=LEVEL)}, sample_channels=BOTH
            ),
            subcolumn=SubColumn.VOLUME,
            expected=f"Volume {LEVEL}",
        ),
        TestCase(
            label="a volume slot spanning no channel",
            row=_row({}),
            subcolumn=SubColumn.VOLUME,
            expected="Volume",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_sentence(self, status: CellStatusText, test_case: TestCase) -> None:
        assert status.describe(test_case.row, None, test_case.subcolumn, VOICES) == test_case.expected
