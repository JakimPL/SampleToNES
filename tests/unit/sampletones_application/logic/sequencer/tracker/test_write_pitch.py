from dataclasses import dataclass
from typing import Final, Optional, Tuple

import pytest

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.tracker import SequencerTrackerLogic
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PERIOD, MIN_PLAYED_PITCH, NUM_PERIODS
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.patterns.pitch import Note, RowPitch, Step
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.sequencer import sample_reconstruction

ROOT_PITCH: Final[int] = 60
TYPED_NOTE: Final[int] = 67
TYPED_STEP: Final[int] = -4
TYPED_PERIOD: Final[int] = 9


def _logic() -> Tuple[ProjectController, SequencerTrackerLogic]:
    controller = ProjectController(ProjectManager())
    return controller, SequencerTrackerLogic(controller)


def _write(
    controller: ProjectController,
    channel: ChannelName,
    row_index: int,
    command: Optional[object],
) -> None:
    pattern_index = controller.project.song.order[0][channel]
    controller.set_row(channel, pattern_index, row_index, command=command)


def _pitch(logic: SequencerTrackerLogic, channel: ChannelName, row_index: int) -> Optional[RowPitch]:
    row = logic.row(channel, row_index)
    return row.pitch if row is not None else None


def _instrument(controller: ProjectController) -> Instrument:
    return controller.add_instrument(
        Instrument(
            name="lead",
            envelopes=InstrumentEnvelopes(volume=Envelope(items=(15,))),
            initial_pitch=ROOT_PITCH,
        )
    )


class TestATypedPitchIsStoredAsWritten(BaseTestSuite):
    """A pitch lands in the face the reader typed, whichever voice the channel carries."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: RowPitch
        pitch: RowPitch
        channel: ChannelName = ChannelName.PULSE1

    test_cases: Tuple["TestATypedPitchIsStoredAsWritten.TestCase", ...] = (
        TestCase(label="a note on an instrument", pitch=Note(value=TYPED_NOTE), expected=Note(value=TYPED_NOTE)),
        TestCase(label="a step on an instrument", pitch=Step(value=TYPED_STEP), expected=Step(value=TYPED_STEP)),
        TestCase(
            label="a note below the channel's range is held at its lowest note",
            pitch=Note(value=MAX_PERIOD + 1),
            expected=Note(value=MIN_PLAYED_PITCH),
        ),
        TestCase(
            label="a period on noise",
            channel=ChannelName.NOISE,
            pitch=Note(value=TYPED_PERIOD),
            expected=Note(value=TYPED_PERIOD),
        ),
        TestCase(
            label="a pitch on noise is held among the sixteen periods",
            channel=ChannelName.NOISE,
            pitch=Note(value=TYPED_NOTE),
            expected=Note(value=MAX_PERIOD),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_pitch_the_row_holds(self, test_case: TestCase) -> None:
        controller, logic = _logic()
        instrument = _instrument(controller)
        _write(controller, test_case.channel, 0, NoteOn(voice_id=instrument.id))

        logic.write_cell(0, test_case.channel, None, test_case.pitch, None)

        assert _pitch(logic, test_case.channel, 0) == test_case.expected


class TestThePitchLandsWhateverTheChannelCarries:
    def test_a_sample_row_takes_a_note(self) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(sample_reconstruction([ChannelName.PULSE1]), name="bass")
        _write(controller, ChannelName.PULSE1, 0, NoteOn(voice_id=sample.id))

        logic.write_cell(0, ChannelName.PULSE1, None, Note(value=TYPED_NOTE), None)

        assert _pitch(logic, ChannelName.PULSE1, 0) == Note(value=TYPED_NOTE)

    def test_a_row_below_the_note_takes_a_note(self) -> None:
        controller, logic = _logic()
        instrument = _instrument(controller)
        _write(controller, ChannelName.PULSE1, 0, NoteOn(voice_id=instrument.id))

        logic.write_cell(2, ChannelName.PULSE1, None, Note(value=TYPED_NOTE), None)

        assert _pitch(logic, ChannelName.PULSE1, 2) == Note(value=TYPED_NOTE)

    def test_a_row_carrying_no_voice_takes_a_note(self) -> None:
        _, logic = _logic()

        logic.write_cell(0, ChannelName.PULSE1, None, Note(value=TYPED_NOTE), None)

        assert _pitch(logic, ChannelName.PULSE1, 0) == Note(value=TYPED_NOTE)

    def test_a_row_past_a_note_off_takes_a_note(self) -> None:
        controller, logic = _logic()
        instrument = _instrument(controller)
        _write(controller, ChannelName.PULSE1, 0, NoteOn(voice_id=instrument.id))
        _write(controller, ChannelName.PULSE1, 1, NoteOff())

        logic.write_cell(2, ChannelName.PULSE1, None, Note(value=TYPED_NOTE), None)

        assert _pitch(logic, ChannelName.PULSE1, 2) == Note(value=TYPED_NOTE)

    def test_the_voice_and_the_volume_stand(self) -> None:
        controller, logic = _logic()
        instrument = _instrument(controller)
        _write(controller, ChannelName.PULSE1, 0, NoteOn(voice_id=instrument.id))
        logic.adjust_volume(ChannelName.PULSE1, 0, -1)

        logic.write_cell(0, ChannelName.PULSE1, None, Step(value=TYPED_STEP), None)

        row = logic.row(ChannelName.PULSE1, 0)
        assert row is not None
        assert row.command == NoteOn(voice_id=instrument.id)
        assert row.volume is not None


class TestANoteWrittenThroughTheSampleColumn:
    """The sample column hands a note to the channels playing the sample, each naming it its own way."""

    def test_the_noise_channel_takes_the_period_the_pitch_names(self) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.NOISE]),
            name="kit",
        )
        logic.place_note(0, None, sample.id)

        logic.write_cell(0, None, None, Note(value=TYPED_NOTE), None)

        assert _pitch(logic, ChannelName.PULSE1, 0) == Note(value=TYPED_NOTE)
        assert _pitch(logic, ChannelName.NOISE, 0) == Note(value=TYPED_NOTE % NUM_PERIODS)

    def test_a_step_reaches_every_channel_as_it_stands(self) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.NOISE]),
            name="kit",
        )
        logic.place_note(0, None, sample.id)

        logic.write_cell(0, None, None, Step(value=TYPED_STEP), None)

        assert _pitch(logic, ChannelName.PULSE1, 0) == Step(value=TYPED_STEP)
        assert _pitch(logic, ChannelName.NOISE, 0) == Step(value=TYPED_STEP)
