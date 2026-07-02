from typing import Callable

from sampletones_application.logic.history.snapshot import fingerprint_project, snapshot_project
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_core.reconstructions import Reconstruction


def _controller() -> ProjectController:
    return ProjectController(ProjectManager())


class TestSnapshotIndependence:
    def test_light_structure_is_deep_copied(self) -> None:
        controller = _controller()
        controller.set_tempo(120)

        snapshot = snapshot_project(controller.project)
        controller.set_tempo(200)

        assert snapshot.settings.tempo == 120
        assert snapshot.song is not controller.project.song

    def test_reconstruction_audio_is_shared(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller = _controller()
        sample = controller.add_sample(reconstruction_factory(), name="lead")

        snapshot = snapshot_project(controller.project)

        assert snapshot.samples[sample.id].reconstruction is sample.reconstruction


class TestFingerprint:
    def test_fingerprint_stable_across_snapshot(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller = _controller()
        controller.add_sample(reconstruction_factory(), name="lead")

        original = fingerprint_project(controller.project)
        snapshot = snapshot_project(controller.project)

        assert fingerprint_project(snapshot) == original

    def test_fingerprint_changes_with_state(self) -> None:
        controller = _controller()
        before = fingerprint_project(controller.project)

        controller.set_tempo(controller.project.settings.tempo + 7)

        assert fingerprint_project(controller.project) != before
