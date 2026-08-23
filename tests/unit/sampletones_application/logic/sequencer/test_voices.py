from typing import Callable, Tuple
from unittest.mock import MagicMock

import numpy as np

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.voices import SequencerVoicesLogic
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_application.view_model.shared.footprint import SampleFootprintViewModel
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.formats.famitracker.footprint import (
    features_footprint,
    reconstruction_footprints,
)
from sampletones_core.project.voices.loop import WHOLE_LOOP_POINT
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.shape import Shape
from sampletones_core.reconstructions import Reconstruction
from tests.suite.sequencer import sample_reconstruction


def _logic() -> Tuple[ProjectController, SequencerVoicesLogic]:
    controller = ProjectController(ProjectManager())
    logic = SequencerVoicesLogic(
        controller,
        MagicMock(),
        MagicMock(),
        scheduling=MagicMock(),
    )
    return controller, logic


def _logic_with_mocks() -> Tuple[
    ProjectController,
    SequencerVoicesLogic,
    MagicMock,
    MagicMock,
]:
    controller = ProjectController(ProjectManager())
    session_manager = MagicMock()
    audio_device_manager = MagicMock()
    logic = SequencerVoicesLogic(
        controller,
        session_manager,
        audio_device_manager,
        scheduling=MagicMock(),
    )
    return controller, logic, session_manager, audio_device_manager


def _place_instrument(
    controller: ProjectController,
    channel: ChannelName,
    voice_id: str,
) -> None:
    pattern_index = controller.project.song.order[0][channel]
    controller.set_row(
        channel,
        pattern_index,
        0,
        command=NoteOn(voice_id=voice_id),
    )


class TestSampleName:
    def test_returns_the_voice_name(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        assert logic.voice_name(sample.id) == "lead"


class TestIsSampleUsed:
    def test_false_for_unreferenced_sample(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        assert logic.is_voice_used(sample.id) is False

    def test_true_after_placing_in_a_pattern(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        _place_instrument(controller, ChannelName.PULSE1, sample.id)
        assert logic.is_voice_used(sample.id) is True


class TestRemoveSample:
    def test_removes_unused_sample_from_pool(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")

        logic.remove_voice(sample.id)

        assert controller.project.voice(sample.id) is None

    def test_removing_used_sample_clears_its_references(
        self, reconstruction_factory: Callable[[], Reconstruction]
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        _place_instrument(controller, ChannelName.PULSE1, sample.id)

        logic.remove_voice(sample.id)

        assert controller.project.voice(sample.id) is None
        assert logic.is_voice_used(sample.id) is False


class TestMoveSample:
    def test_move_sample_reorders_pool(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        first = controller.add_sample(reconstruction_factory(), name="first")
        controller.add_sample(reconstruction_factory(), name="second")

        logic.move_voice(first.id, 1)

        assert [sample.name for sample in controller.project.voices] == [
            "second",
            "first",
        ]


class TestDuplicateSample:
    def test_duplicate_sample_appends_copy(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        source = controller.add_sample(reconstruction_factory(), name="lead")

        logic.duplicate_voice(source.id)

        assert [sample.name for sample in controller.project.voices] == [
            "lead",
            "lead",
        ]


class TestBuildSamples:
    def test_lists_added_samples_in_insertion_order(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        first = controller.add_sample(reconstruction_factory(), name="first")
        second = controller.add_sample(reconstruction_factory(), name="second")

        view_model = logic.build_voices()

        assert [entry.voice_id for entry in view_model.voices] == [
            first.id,
            second.id,
        ]
        assert [entry.name for entry in view_model.voices] == [
            "first",
            "second",
        ]


class TestBuildSampleFootprint:
    """The samples menu prints what a sample occupies, measured the way the sample is placed."""

    def test_it_names_each_playing_channel(self) -> None:
        controller, logic = _logic()
        channels = (ChannelName.PULSE1, ChannelName.TRIANGLE)
        sample = controller.add_sample(sample_reconstruction(channels), name="bell")

        footprint = logic.build_voice_footprint(sample.id)

        assert footprint is not None
        assert [instrument.channel for instrument in footprint.instruments] == list(channels)

    def test_it_measures_the_sample_under_its_own_loop_flag(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        controller.set_voice_loop_point(sample.id, WHOLE_LOOP_POINT)

        footprint = logic.build_voice_footprint(sample.id)

        assert footprint == SampleFootprintViewModel.from_footprints(
            reconstruction_footprints(sample.reconstruction, loop_point=WHOLE_LOOP_POINT)
        )

    def test_a_looping_sample_costs_less_than_a_one_shot(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        """A looping instrument shares the shortest dimension's length, so it stores fewer items."""
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        one_shot = logic.build_voice_footprint(sample.id)

        controller.set_voice_loop_point(sample.id, WHOLE_LOOP_POINT)
        looping = logic.build_voice_footprint(sample.id)

        assert one_shot is not None and looping is not None
        assert looping.total_bytes < one_shot.total_bytes

    def test_each_channel_is_measured_as_the_instrument_it_sounds(self) -> None:
        """A channel's figure is the cost of its own instrument, and the channels differ.

        The triangle states a pitch alone where the pulse states a level and a waveform too, so
        the same frame written on each costs the triangle the less.
        """
        controller, logic = _logic()
        channels = (ChannelName.PULSE1, ChannelName.TRIANGLE)
        sample = controller.add_sample(sample_reconstruction(channels), name="bell")

        footprint = logic.build_voice_footprint(sample.id)

        assert footprint is not None
        assert footprint.bytes_for(ChannelName.TRIANGLE) < footprint.bytes_for(ChannelName.PULSE1)

    def test_a_sample_the_pool_has_dropped_is_measured_nowhere(self) -> None:
        _, logic = _logic()

        assert logic.build_voice_footprint("missing") is None


class TestPlaySample:
    def test_plays_reconstruction_regardless_of_autoplay(
        self, reconstruction_factory: Callable[[], Reconstruction]
    ) -> None:
        controller, logic, session_manager, audio_device_manager = _logic_with_mocks()
        session_manager.autoplay = False
        sample = controller.add_sample(reconstruction_factory(), name="lead")

        logic.play_voice(sample.id)

        audio_device_manager.play.assert_called_once()
        call = audio_device_manager.play.call_args
        assert np.array_equal(call.args[0], sample.reconstruction.approximation)
        assert call.kwargs["priority"] == PlaybackPriority.NORMAL
        assert call.kwargs["update"] is False

    def test_unknown_sample_is_ignored(self) -> None:
        _, logic, _, audio_device_manager = _logic_with_mocks()

        logic.play_voice("missing")

        audio_device_manager.play.assert_not_called()


class TestAutoplay:
    def test_executes_pending_preview_when_autoplay_enabled(
        self, reconstruction_factory: Callable[[], Reconstruction]
    ) -> None:
        controller, logic, session_manager, audio_device_manager = _logic_with_mocks()
        session_manager.autoplay = True
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        logic._pending_autoplay_sample = sample.id

        logic._execute_autoplay()

        audio_device_manager.play.assert_called_once()
        assert audio_device_manager.play.call_args.kwargs["priority"] == PlaybackPriority.PREVIEW

    def test_skips_pending_preview_when_autoplay_disabled(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic, session_manager, audio_device_manager = _logic_with_mocks()
        session_manager.autoplay = False
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        logic._pending_autoplay_sample = sample.id

        logic._execute_autoplay()

        audio_device_manager.play.assert_not_called()

    def test_cancel_autoplay_drops_pending_preview(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic, session_manager, audio_device_manager = _logic_with_mocks()
        session_manager.autoplay = True
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        logic._pending_autoplay_sample = sample.id

        logic.cancel_autoplay()
        logic._execute_autoplay()

        audio_device_manager.play.assert_not_called()

    def test_request_edit_cancels_pending_preview(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic, session_manager, audio_device_manager = _logic_with_mocks()
        session_manager.autoplay = True
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        logic._pending_autoplay_sample = sample.id

        logic.request_edit(sample.id)
        logic._execute_autoplay()

        audio_device_manager.play.assert_not_called()


class TestShapesInTheVoiceList:
    """A hand-written voice sits in the same list as a converted one, marked by its kind."""

    def test_a_shape_is_listed_beside_the_samples_that_were_added(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="bass")
        shape = logic.add_shape("lead")

        entries = logic.build_voices().voices

        assert [(entry.voice_id, entry.kind) for entry in entries] == [
            (sample.id, VoiceKind.SAMPLE),
            (shape.id, VoiceKind.SHAPE),
        ]

    def test_a_shape_is_measured_as_the_one_instrument_it_exports(self) -> None:
        controller, logic = _logic()
        shape = logic.add_shape("lead")
        controller.set_shape_envelope(shape.id, FeatureKey.VOLUME, (15, 12, 9))

        footprint = logic.build_voice_footprint(shape.id)

        assert footprint is not None
        assert (
            footprint.total_bytes
            == features_footprint(
                shape.instrument_features(),
                loop_point=shape.loop_point,
            ).total_bytes
        )
        assert [instrument.channel for instrument in footprint.instruments] == [None]

    def test_a_shape_previews_through_the_pulse_channel(self) -> None:
        controller, logic, session_manager, audio_device_manager = _logic_with_mocks()
        shape = logic.add_shape("lead")
        controller.set_shape_envelope(shape.id, FeatureKey.VOLUME, (15, 12))

        logic.play_voice(shape.id)

        played = audio_device_manager.play.call_args.args[0]
        assert played.size > 0

    def test_a_shape_writing_nothing_sounds_no_preview(self) -> None:
        controller, logic, _, audio_device_manager = _logic_with_mocks()
        shape = controller.add_shape(Shape(name="lead"))

        logic.play_voice(shape.id)

        audio_device_manager.play.assert_not_called()
