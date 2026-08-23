from typing import Final, Optional, Tuple

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.tracker import SequencerTrackerLogic
from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.voices.creation import new_shape
from sampletones_core.project.voices.envelopes import ShapeEnvelopes
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.voice import voice_reference
from tests.suite.sequencer import sample_reconstruction

ROOT_PITCH: Final[int] = 60
TYPED_PITCH: Final[int] = 67


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


def _transpose(logic: SequencerTrackerLogic, channel: ChannelName, row_index: int) -> Optional[int]:
    row = logic.row(channel, row_index)
    return row.transpose if row is not None else None


class TestATypedNoteIsStatedAsAStepFromTheVoice:
    def test_a_shape_takes_the_step_that_reaches_the_note(self) -> None:
        controller, logic = _logic()
        shape = controller.add_shape(new_shape("lead"))
        controller.set_shape_root(shape.id, pitch=ROOT_PITCH, period=8)
        shape.envelopes = ShapeEnvelopes(volume=(15,))
        shape.invalidate()
        _write(controller, ChannelName.PULSE1, 0, NoteOn(voice_id=shape.id))

        logic.write_note(0, ChannelName.PULSE1, TYPED_PITCH)

        assert _transpose(logic, ChannelName.PULSE1, 0) == TYPED_PITCH - ROOT_PITCH

    def test_a_sample_takes_the_step_from_its_own_pitch(self) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(sample_reconstruction([ChannelName.PULSE1]), name="bass")
        _write(controller, ChannelName.PULSE1, 0, NoteOn(voice_id=sample.id))

        logic.write_note(0, ChannelName.PULSE1, TYPED_PITCH)

        expected = TYPED_PITCH - voice_reference(sample, ChannelName.PULSE1)
        assert _transpose(logic, ChannelName.PULSE1, 0) == expected

    def test_a_row_below_the_note_is_measured_against_the_voice_it_carries(self) -> None:
        controller, logic = _logic()
        shape = controller.add_shape(new_shape("lead"))
        controller.set_shape_root(shape.id, pitch=ROOT_PITCH, period=8)
        _write(controller, ChannelName.PULSE1, 0, NoteOn(voice_id=shape.id))

        logic.write_note(2, ChannelName.PULSE1, TYPED_PITCH)

        assert _transpose(logic, ChannelName.PULSE1, 2) == TYPED_PITCH - ROOT_PITCH

    def test_a_row_carrying_no_voice_is_left_as_it_stands(self) -> None:
        _, logic = _logic()

        logic.write_note(0, ChannelName.PULSE1, TYPED_PITCH)

        assert _transpose(logic, ChannelName.PULSE1, 0) is None

    def test_a_row_past_a_note_off_carries_no_voice(self) -> None:
        controller, logic = _logic()
        shape = controller.add_shape(new_shape("lead"))
        _write(controller, ChannelName.PULSE1, 0, NoteOn(voice_id=shape.id))
        _write(controller, ChannelName.PULSE1, 1, NoteOff())

        logic.write_note(2, ChannelName.PULSE1, TYPED_PITCH)

        assert _transpose(logic, ChannelName.PULSE1, 2) is None
