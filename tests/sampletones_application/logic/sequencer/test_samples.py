from typing import Callable, Tuple

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.samples import SequencerSamplesLogic
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.reconstructions import Reconstruction


def _logic() -> Tuple[ProjectController, SequencerSamplesLogic]:
    controller = ProjectController(ProjectManager())
    return controller, SequencerSamplesLogic(controller)


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


class TestBuildSamples:
    def test_lists_added_samples_in_insertion_order(
        self, reconstruction_factory: Callable[[], Reconstruction]
    ) -> None:
        controller, logic = _logic()
        first = controller.add_sample(reconstruction_factory(), name="first")
        second = controller.add_sample(reconstruction_factory(), name="second")

        view_model = logic.build_samples()

        assert [entry.sample_id for entry in view_model.samples] == [first.id, second.id]
        assert [entry.name for entry in view_model.samples] == ["first", "second"]
