from typing import Callable, Tuple
from unittest.mock import MagicMock

import numpy as np

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.samples import SequencerSamplesLogic
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.view_model.shared.footprint import SampleFootprintViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_core.formats.famitracker.footprint import reconstruction_footprints
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.reconstructions import Reconstruction
from tests.suite.sequencer import sample_reconstruction


def _logic() -> Tuple[ProjectController, SequencerSamplesLogic]:
    controller = ProjectController(ProjectManager())
    logic = SequencerSamplesLogic(
        controller,
        MagicMock(),
        MagicMock(),
        scheduling=MagicMock(),
    )
    return controller, logic


def _logic_with_mocks() -> Tuple[
    ProjectController,
    SequencerSamplesLogic,
    MagicMock,
    MagicMock,
]:
    controller = ProjectController(ProjectManager())
    session_manager = MagicMock()
    audio_device_manager = MagicMock()
    logic = SequencerSamplesLogic(
        controller,
        session_manager,
        audio_device_manager,
        scheduling=MagicMock(),
    )
    return controller, logic, session_manager, audio_device_manager


def _place_instrument(
    controller: ProjectController,
    channel: ChannelName,
    sample_id: str,
) -> None:
    pattern_index = controller.project.song.order[0][channel]
    controller.set_row(
        channel,
        pattern_index,
        0,
        command=Instrument(sample_id=sample_id, channel_name=channel),
    )


class TestSampleName:
    def test_returns_the_sample_name(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        assert logic.sample_name(sample.id) == "lead"


class TestIsSampleUsed:
    def test_false_for_unreferenced_sample(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        assert logic.is_sample_used(sample.id) is False

    def test_true_after_placing_in_a_pattern(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        _place_instrument(controller, ChannelName.PULSE1, sample.id)
        assert logic.is_sample_used(sample.id) is True


class TestRemoveSample:
    def test_removes_unused_sample_from_pool(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")

        logic.remove_sample(sample.id)

        assert controller.project.sample(sample.id) is None

    def test_removing_used_sample_clears_its_references(
        self, reconstruction_factory: Callable[[], Reconstruction]
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        _place_instrument(controller, ChannelName.PULSE1, sample.id)

        logic.remove_sample(sample.id)

        assert controller.project.sample(sample.id) is None
        assert logic.is_sample_used(sample.id) is False


class TestMoveSample:
    def test_move_sample_reorders_pool(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        first = controller.add_sample(reconstruction_factory(), name="first")
        controller.add_sample(reconstruction_factory(), name="second")

        logic.move_sample(first.id, 1)

        assert [sample.name for sample in controller.project.samples] == [
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

        logic.duplicate_sample(source.id)

        assert [sample.name for sample in controller.project.samples] == [
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

        view_model = logic.build_samples()

        assert [entry.sample_id for entry in view_model.samples] == [
            first.id,
            second.id,
        ]
        assert [entry.name for entry in view_model.samples] == [
            "first",
            "second",
        ]


class TestBuildSampleFootprint:
    """The samples menu prints what a sample occupies, measured the way the sample is placed."""

    def test_it_names_each_playing_channel(self) -> None:
        controller, logic = _logic()
        channels = (ChannelName.PULSE1, ChannelName.TRIANGLE)
        sample = controller.add_sample(sample_reconstruction(channels), name="bell")

        footprint = logic.build_sample_footprint(sample.id)

        assert footprint is not None
        assert [instrument.channel for instrument in footprint.instruments] == list(channels)

    def test_it_measures_the_sample_under_its_own_loop_flag(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        controller.set_sample_loop(sample.id, True)

        footprint = logic.build_sample_footprint(sample.id)

        assert footprint == SampleFootprintViewModel.from_footprints(
            reconstruction_footprints(sample.reconstruction, loop=True)
        )

    def test_a_looping_sample_costs_less_than_a_one_shot(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        """A looping instrument shares the shortest dimension's length, so it stores fewer items."""
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        one_shot = logic.build_sample_footprint(sample.id)

        controller.set_sample_loop(sample.id, True)
        looping = logic.build_sample_footprint(sample.id)

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

        footprint = logic.build_sample_footprint(sample.id)

        assert footprint is not None
        assert footprint.bytes_for(ChannelName.TRIANGLE) < footprint.bytes_for(ChannelName.PULSE1)

    def test_a_sample_the_pool_has_dropped_is_measured_nowhere(self) -> None:
        _, logic = _logic()

        assert logic.build_sample_footprint("missing") is None


class TestPlaySample:
    def test_plays_reconstruction_regardless_of_autoplay(
        self, reconstruction_factory: Callable[[], Reconstruction]
    ) -> None:
        controller, logic, session_manager, audio_device_manager = _logic_with_mocks()
        session_manager.autoplay = False
        sample = controller.add_sample(reconstruction_factory(), name="lead")

        logic.play_sample(sample.id)

        audio_device_manager.play.assert_called_once()
        call = audio_device_manager.play.call_args
        assert np.array_equal(call.args[0], sample.reconstruction.approximation)
        assert call.kwargs["priority"] == PlaybackPriority.NORMAL
        assert call.kwargs["update"] is False

    def test_unknown_sample_is_ignored(self) -> None:
        _, logic, _, audio_device_manager = _logic_with_mocks()

        logic.play_sample("missing")

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
