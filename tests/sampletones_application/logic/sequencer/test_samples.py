from typing import Callable, Tuple
from unittest.mock import MagicMock

import numpy as np

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.samples import SequencerSamplesLogic
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.reconstructions import Reconstruction


def _logic() -> Tuple[ProjectController, SequencerSamplesLogic]:
    controller = ProjectController(ProjectManager())
    logic = SequencerSamplesLogic(
        controller,
        MagicMock(),
        MagicMock(),
        scheduling=MagicMock(),
    )
    return controller, logic


def _logic_with_mocks() -> Tuple[ProjectController, SequencerSamplesLogic, MagicMock, MagicMock]:
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


def _place_instrument(controller: ProjectController, generator: GeneratorName, sample_id: str) -> None:
    pattern_index = controller.project.song.order[0][generator]
    controller.set_row(
        generator,
        pattern_index,
        0,
        instrument=Instrument(sample_id=sample_id, generator_name=generator),
    )


class TestSampleName:
    def test_returns_the_sample_name(self, reconstruction_factory: Callable[[], Reconstruction]) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        assert logic.sample_name(sample.id) == "lead"


class TestIsSampleUsed:
    def test_false_for_unreferenced_sample(self, reconstruction_factory: Callable[[], Reconstruction]) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        assert logic.is_sample_used(sample.id) is False

    def test_true_after_placing_in_a_pattern(self, reconstruction_factory: Callable[[], Reconstruction]) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        _place_instrument(controller, GeneratorName.PULSE1, sample.id)
        assert logic.is_sample_used(sample.id) is True


class TestRemoveSample:
    def test_removes_unused_sample_from_pool(self, reconstruction_factory: Callable[[], Reconstruction]) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")

        logic.remove_sample(sample.id)

        assert controller.project.sample(sample.id) is None

    def test_removing_used_sample_clears_its_references(
        self, reconstruction_factory: Callable[[], Reconstruction]
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        _place_instrument(controller, GeneratorName.PULSE1, sample.id)

        logic.remove_sample(sample.id)

        assert controller.project.sample(sample.id) is None
        assert logic.is_sample_used(sample.id) is False


class TestMoveSample:
    def test_move_sample_reorders_pool(self, reconstruction_factory: Callable[[], Reconstruction]) -> None:
        controller, logic = _logic()
        first = controller.add_sample(reconstruction_factory(), name="first")
        controller.add_sample(reconstruction_factory(), name="second")

        logic.move_sample(first.id, 1)

        assert [sample.name for sample in controller.project.samples] == ["second", "first"]


class TestBuildSamples:
    def test_lists_added_samples_in_insertion_order(self, reconstruction_factory: Callable[[], Reconstruction]) -> None:
        controller, logic = _logic()
        first = controller.add_sample(reconstruction_factory(), name="first")
        second = controller.add_sample(reconstruction_factory(), name="second")

        view_model = logic.build_samples()

        assert [entry.sample_id for entry in view_model.samples] == [first.id, second.id]
        assert [entry.name for entry in view_model.samples] == ["first", "second"]


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

    def test_request_edit_cancels_pending_preview(self, reconstruction_factory: Callable[[], Reconstruction]) -> None:
        controller, logic, session_manager, audio_device_manager = _logic_with_mocks()
        session_manager.autoplay = True
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        logic._pending_autoplay_sample = sample.id

        logic.request_edit(sample.id)
        logic._execute_autoplay()

        audio_device_manager.play.assert_not_called()
