from typing import Callable

import pytest

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.shared.project_source import (
    ProjectSnapshot,
    ProjectSource,
    snapshot_project,
)
from sampletones_core.reconstructions import Reconstruction
from tests.suite.base import BaseTestSuite


@pytest.fixture
def project_controller() -> ProjectController:
    return ProjectController(ProjectManager())


class TestSnapshotIndependence(BaseTestSuite):
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


class TestASnapshotIsASource(BaseTestSuite):
    """A captured document reads as the source a synthesiser takes."""

    def test_the_live_controller_is_a_source(self, project_controller: ProjectController) -> None:
        source: ProjectSource = project_controller

        assert source.project is project_controller.project

    def test_a_snapshot_is_a_source(self, project_controller: ProjectController) -> None:
        source: ProjectSource = ProjectSnapshot.capture(project_controller)

        assert source.project.settings.tempo == project_controller.project.settings.tempo

    def test_the_document_stands_still_while_the_project_moves_on(
        self,
        project_controller: ProjectController,
    ) -> None:
        project_controller.set_tempo(120)

        snapshot = ProjectSnapshot.capture(project_controller)
        project_controller.set_tempo(200)

        assert snapshot.project.settings.tempo == 120
