from typing import Final, Optional, Tuple

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.tracker import SequencerTrackerLogic
from sampletones_core.constants.enums import ChannelName
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.voices.creation import new_instrument
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.utils.display import NOTE_BLANK, display_transpose
from sampletones_core.utils.frequencies import period_to_name, pitch_to_name
from tests.suite.sequencer import sample_reconstruction

ROOT_PITCH: Final[int] = 60
ROOT_PERIOD: Final[int] = 5
TRANSPOSE: Final[int] = 4
BEND: Final[int] = 7


def _logic() -> Tuple[ProjectController, SequencerTrackerLogic]:
    controller = ProjectController(ProjectManager())
    return controller, SequencerTrackerLogic(controller)


def _instrument(controller: ProjectController) -> Instrument:
    instrument = controller.add_instrument(new_instrument("lead"))
    controller.set_instrument_root(instrument.id, pitch=ROOT_PITCH, period=ROOT_PERIOD)
    instrument.envelopes = InstrumentEnvelopes(volume=Envelope(items=(15,)))
    instrument.invalidate()
    return instrument


def _write(
    controller: ProjectController,
    channel: ChannelName,
    row_index: int,
    *,
    command: Optional[object] = None,
    transpose: Optional[int] = None,
) -> None:
    pattern_index = controller.project.song.order[0][channel]
    controller.set_row(
        channel,
        pattern_index,
        row_index,
        command=command,
        transpose=transpose,
    )


def _pitch_cell(logic: SequencerTrackerLogic, channel: ChannelName, row_index: int) -> str:
    return logic.build_grid().rows[row_index].cells[channel].transpose


class TestACellReadsInTheTermsOfItsVoice:
    def test_a_sample_reads_as_a_step_from_its_own_pitch(self) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(sample_reconstruction([ChannelName.PULSE1]), name="bass")
        _write(controller, ChannelName.PULSE1, 0, command=NoteOn(voice_id=sample.id), transpose=TRANSPOSE)

        assert _pitch_cell(logic, ChannelName.PULSE1, 0) == display_transpose(TRANSPOSE)

    def test_an_instrument_reads_as_the_note_it_sounds(self) -> None:
        controller, logic = _logic()
        instrument = _instrument(controller)
        _write(controller, ChannelName.PULSE1, 0, command=NoteOn(voice_id=instrument.id), transpose=TRANSPOSE)

        assert _pitch_cell(logic, ChannelName.PULSE1, 0) == pitch_to_name(ROOT_PITCH + TRANSPOSE)

    def test_an_instrument_on_noise_names_its_period(self) -> None:
        controller, logic = _logic()
        instrument = _instrument(controller)
        _write(controller, ChannelName.NOISE, 0, command=NoteOn(voice_id=instrument.id), transpose=TRANSPOSE)

        assert _pitch_cell(logic, ChannelName.NOISE, 0) == period_to_name(ROOT_PERIOD + TRANSPOSE)

    def test_an_empty_cell_reads_blank_whichever_voice_is_carried(self) -> None:
        controller, logic = _logic()
        instrument = _instrument(controller)
        _write(controller, ChannelName.PULSE1, 0, command=NoteOn(voice_id=instrument.id), transpose=TRANSPOSE)

        assert _pitch_cell(logic, ChannelName.PULSE1, 1) == NOTE_BLANK


class TestTheFaceFollowsTheVoiceTheChannelCarries:
    def test_a_bend_below_an_instrument_still_reads_as_a_note(self) -> None:
        """A row bending a note it did not start reads in the terms of the voice in force."""
        controller, logic = _logic()
        instrument = _instrument(controller)
        _write(controller, ChannelName.PULSE1, 0, command=NoteOn(voice_id=instrument.id), transpose=0)
        _write(controller, ChannelName.PULSE1, 1, transpose=BEND)

        assert _pitch_cell(logic, ChannelName.PULSE1, 1) == pitch_to_name(ROOT_PITCH + BEND)

    def test_a_bend_below_a_sample_still_reads_as_a_step(self) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(sample_reconstruction([ChannelName.PULSE1]), name="bass")
        _write(controller, ChannelName.PULSE1, 0, command=NoteOn(voice_id=sample.id), transpose=0)
        _write(controller, ChannelName.PULSE1, 1, transpose=BEND)

        assert _pitch_cell(logic, ChannelName.PULSE1, 1) == display_transpose(BEND)

    def test_a_note_off_hands_the_column_back_to_the_neutral_face(self) -> None:
        controller, logic = _logic()
        instrument = _instrument(controller)
        _write(controller, ChannelName.PULSE1, 0, command=NoteOn(voice_id=instrument.id), transpose=0)
        _write(controller, ChannelName.PULSE1, 1, command=NoteOff())
        _write(controller, ChannelName.PULSE1, 2, transpose=BEND)

        assert _pitch_cell(logic, ChannelName.PULSE1, 2) == display_transpose(BEND)

    def test_a_frame_naming_no_voice_reads_as_a_step(self) -> None:
        controller, logic = _logic()
        _write(controller, ChannelName.PULSE1, 0, transpose=BEND)

        assert _pitch_cell(logic, ChannelName.PULSE1, 0) == display_transpose(BEND)


class TestTheSampleColumnSpeaksForSamples:
    def test_it_declines_an_instrument(self) -> None:
        controller, logic = _logic()
        instrument = _instrument(controller)

        logic.set_row_sample(0, instrument.id)

        assert all(logic.row(channel, 0) is None or logic.row(channel, 0).is_empty() for channel in ChannelName.items())

    def test_it_reads_mixed_where_the_channels_disagree_on_the_face(self) -> None:
        controller, logic = _logic()
        instrument = _instrument(controller)
        sample = controller.add_sample(sample_reconstruction(list(ChannelName.items())), name="bass")
        _write(controller, ChannelName.PULSE1, 0, command=NoteOn(voice_id=instrument.id), transpose=0)
        _write(controller, ChannelName.PULSE2, 0, command=NoteOn(voice_id=sample.id), transpose=0)

        assert logic.build_grid().rows[0].transpose == "?"
