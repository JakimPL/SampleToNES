from typing import Callable

from sampletones_application.logic.history.snapshot import fingerprint_project, snapshot_project
from sampletones_application.logic.project.controller import ProjectController
from sampletones_core.reconstructions import Reconstruction


class TestSnapshotIndependence:
    def test_light_structure_is_deep_copied(self, project_controller: ProjectController) -> None:
        project_controller.set_tempo(120)

        snapshot = snapshot_project(project_controller.project)
        project_controller.set_tempo(200)

        assert snapshot.settings.tempo == 120
        assert snapshot.song is not project_controller.project.song

    def test_reconstruction_audio_is_shared(
        self,
        project_controller: ProjectController,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        sample = project_controller.add_sample(reconstruction_factory(), name="lead")

        snapshot = snapshot_project(project_controller.project)

        assert snapshot.samples[sample.id].reconstruction is sample.reconstruction


class TestFingerprint:
    def test_fingerprint_stable_across_snapshot(
        self,
        project_controller: ProjectController,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        project_controller.add_sample(reconstruction_factory(), name="lead")

        original = fingerprint_project(project_controller.project)
        snapshot = snapshot_project(project_controller.project)

        assert fingerprint_project(snapshot) == original

    def test_fingerprint_changes_with_state(self, project_controller: ProjectController) -> None:
        before = fingerprint_project(project_controller.project)

        project_controller.set_tempo(project_controller.project.settings.tempo + 7)

        assert fingerprint_project(project_controller.project) != before
