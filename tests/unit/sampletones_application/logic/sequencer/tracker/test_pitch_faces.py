from typing import Final, Optional, Tuple

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.tracker import SequencerTrackerLogic
from sampletones_core.constants.enums import ChannelName
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.patterns.pitch import Note, RowPitch, Step
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.utils.display import NOTE_BLANK, display_transpose
from sampletones_core.utils.frequencies import period_to_name, pitch_to_name
from sampletones_shared.constants.symbols import MIXED
from tests.suite.sequencer import sample_reconstruction

ROOT_PITCH: Final[int] = 60
ROOT_PERIOD: Final[int] = 5
STEP: Final[int] = 4
NOTE: Final[int] = 64
PERIOD: Final[int] = 9
BEND: Final[int] = 7


def _logic() -> Tuple[ProjectController, SequencerTrackerLogic]:
    controller = ProjectController(ProjectManager())
    return controller, SequencerTrackerLogic(controller)


def _instrument(controller: ProjectController) -> Instrument:
    return controller.add_instrument(
        Instrument(
            name="lead",
            envelopes=InstrumentEnvelopes(volume=Envelope(items=(15,))),
            initial_pitch=ROOT_PITCH,
            initial_period=ROOT_PERIOD,
        )
    )


def _write(
    controller: ProjectController,
    channel: ChannelName,
    row_index: int,
    *,
    command: Optional[object] = None,
    pitch: Optional[RowPitch] = None,
) -> None:
    pattern_index = controller.project.song.order[0][channel]
    controller.set_row(
        channel,
        pattern_index,
        row_index,
        command=command,
        pitch=pitch,
    )


def _pitch_cell(logic: SequencerTrackerLogic, channel: ChannelName, row_index: int) -> str:
    return logic.build_grid().rows[row_index].cells[channel].transpose


class TestACellReadsTheFaceItWasWrittenIn:
    def test_a_step_on_a_sample_reads_as_the_step(self) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(sample_reconstruction([ChannelName.PULSE1]), name="bass")
        _write(controller, ChannelName.PULSE1, 0, command=NoteOn(voice_id=sample.id), pitch=Step(value=STEP))

        assert _pitch_cell(logic, ChannelName.PULSE1, 0) == display_transpose(STEP)

    def test_a_note_on_a_sample_reads_as_the_note(self) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(sample_reconstruction([ChannelName.PULSE1]), name="bass")
        _write(controller, ChannelName.PULSE1, 0, command=NoteOn(voice_id=sample.id), pitch=Note(value=NOTE))

        assert _pitch_cell(logic, ChannelName.PULSE1, 0) == pitch_to_name(NOTE)

    def test_a_step_on_an_instrument_reads_as_the_step(self) -> None:
        controller, logic = _logic()
        instrument = _instrument(controller)
        _write(controller, ChannelName.PULSE1, 0, command=NoteOn(voice_id=instrument.id), pitch=Step(value=STEP))

        assert _pitch_cell(logic, ChannelName.PULSE1, 0) == display_transpose(STEP)

    def test_a_note_on_an_instrument_reads_as_the_note(self) -> None:
        controller, logic = _logic()
        instrument = _instrument(controller)
        _write(controller, ChannelName.PULSE1, 0, command=NoteOn(voice_id=instrument.id), pitch=Note(value=NOTE))

        assert _pitch_cell(logic, ChannelName.PULSE1, 0) == pitch_to_name(NOTE)

    def test_a_note_on_noise_names_its_period(self) -> None:
        controller, logic = _logic()
        instrument = _instrument(controller)
        _write(controller, ChannelName.NOISE, 0, command=NoteOn(voice_id=instrument.id), pitch=Note(value=PERIOD))

        assert _pitch_cell(logic, ChannelName.NOISE, 0) == period_to_name(PERIOD)

    def test_an_empty_cell_reads_blank_whichever_voice_is_carried(self) -> None:
        controller, logic = _logic()
        instrument = _instrument(controller)
        _write(controller, ChannelName.PULSE1, 0, command=NoteOn(voice_id=instrument.id), pitch=Note(value=NOTE))

        assert _pitch_cell(logic, ChannelName.PULSE1, 1) == NOTE_BLANK


class TestTheFaceStandsWhereverTheRowStands:
    def test_a_bend_below_an_instrument_reads_what_it_stores(self) -> None:
        controller, logic = _logic()
        instrument = _instrument(controller)
        _write(controller, ChannelName.PULSE1, 0, command=NoteOn(voice_id=instrument.id), pitch=Note(value=NOTE))
        _write(controller, ChannelName.PULSE1, 1, pitch=Step(value=BEND))

        assert _pitch_cell(logic, ChannelName.PULSE1, 1) == display_transpose(BEND)

    def test_a_bend_below_a_sample_reads_what_it_stores(self) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(sample_reconstruction([ChannelName.PULSE1]), name="bass")
        _write(controller, ChannelName.PULSE1, 0, command=NoteOn(voice_id=sample.id), pitch=Step(value=0))
        _write(controller, ChannelName.PULSE1, 1, pitch=Note(value=NOTE))

        assert _pitch_cell(logic, ChannelName.PULSE1, 1) == pitch_to_name(NOTE)

    def test_a_row_past_a_note_off_reads_what_it_stores(self) -> None:
        controller, logic = _logic()
        instrument = _instrument(controller)
        _write(controller, ChannelName.PULSE1, 0, command=NoteOn(voice_id=instrument.id), pitch=Note(value=NOTE))
        _write(controller, ChannelName.PULSE1, 1, command=NoteOff())
        _write(controller, ChannelName.PULSE1, 2, pitch=Note(value=NOTE))

        assert _pitch_cell(logic, ChannelName.PULSE1, 2) == pitch_to_name(NOTE)

    def test_a_frame_naming_no_voice_reads_what_it_stores(self) -> None:
        controller, logic = _logic()
        _write(controller, ChannelName.PULSE1, 0, pitch=Step(value=BEND))

        assert _pitch_cell(logic, ChannelName.PULSE1, 0) == display_transpose(BEND)


class TestTheSampleColumnSpeaksForSamples:
    def test_it_declines_an_instrument(self) -> None:
        controller, logic = _logic()
        instrument = _instrument(controller)

        logic.set_row_sample(0, instrument.id)

        assert all(logic.row(channel, 0) is None or logic.row(channel, 0).is_empty() for channel in ChannelName.items())

    def test_it_reads_mixed_where_the_channels_disagree_on_the_face(self) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(sample_reconstruction([ChannelName.PULSE1, ChannelName.PULSE2]), name="bass")
        _write(controller, ChannelName.PULSE1, 0, command=NoteOn(voice_id=sample.id), pitch=Step(value=0))
        _write(controller, ChannelName.PULSE2, 0, command=NoteOn(voice_id=sample.id), pitch=Note(value=ROOT_PITCH))

        assert logic.build_grid().rows[0].transpose == MIXED
