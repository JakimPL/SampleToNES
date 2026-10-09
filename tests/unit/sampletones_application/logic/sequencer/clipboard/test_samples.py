import pytest

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.clipboard.samples import (
    ProjectSampleDirectory,
)
from sampletones_core.constants.enums import ChannelName
from tests.suite.sequencer import sample_reconstruction


@pytest.fixture
def controller() -> ProjectController:
    controller = ProjectController(ProjectManager())
    controller.new()
    return controller


@pytest.fixture
def directory(controller: ProjectController) -> ProjectSampleDirectory:
    return ProjectSampleDirectory(controller)


def _add_sample(controller: ProjectController, name: str) -> str:
    sample = controller.add_sample(
        sample_reconstruction([ChannelName.PULSE1]),
        name=name,
    )
    return sample.id


class TestReadingBothWays:
    def test_a_sample_stands_at_the_position_it_is_listed_at(
        self,
        controller: ProjectController,
        directory: ProjectSampleDirectory,
    ) -> None:
        first = _add_sample(controller, "kick")
        second = _add_sample(controller, "snare")

        assert directory.position_of(first) == 0
        assert directory.position_of(second) == 1
        assert directory.sample_at(0) == first
        assert directory.sample_at(1) == second

    def test_a_sample_the_project_lacks_stands_nowhere(
        self,
        directory: ProjectSampleDirectory,
    ) -> None:
        assert directory.position_of("absent") is None

    def test_a_position_the_list_falls_short_of_names_no_sample(
        self,
        controller: ProjectController,
        directory: ProjectSampleDirectory,
    ) -> None:
        _add_sample(controller, "kick")

        assert directory.sample_at(1) is None
        assert directory.sample_at(-1) is None


class TestFollowingTheProject:
    def test_a_sample_added_later_is_reached(
        self,
        controller: ProjectController,
        directory: ProjectSampleDirectory,
    ) -> None:
        """The project is read on each lookup, so an undo putting another one in place is followed."""
        assert directory.sample_at(0) is None

        added = _add_sample(controller, "hat")

        assert directory.sample_at(0) == added
