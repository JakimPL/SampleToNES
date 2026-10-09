import pytest

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.shared.project_source import (
    ProjectSnapshot,
    ProjectSource,
)
from tests.suite.base import BaseTestSuite


@pytest.fixture
def project_controller() -> ProjectController:
    return ProjectController(ProjectManager())


class TestASnapshotIsASource(BaseTestSuite):
    """A captured document reads as the source a synthesizer takes."""

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
