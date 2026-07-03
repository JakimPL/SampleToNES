from typing import Final, Protocol, Tuple

import pytest

from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager

DEFAULT_HISTORY_BUDGET: Final[int] = 10


class HistoryFactory(Protocol):
    def __call__(
        self,
        *,
        strict: bool = True,
        budget: int = DEFAULT_HISTORY_BUDGET,
    ) -> Tuple[ProjectController, HistoryManager]: ...


@pytest.fixture
def project_controller() -> ProjectController:
    return ProjectController(ProjectManager())


@pytest.fixture
def history_factory() -> HistoryFactory:
    def build(
        *,
        strict: bool = True,
        budget: int = DEFAULT_HISTORY_BUDGET,
    ) -> Tuple[ProjectController, HistoryManager]:
        controller = ProjectController(ProjectManager())
        history = HistoryManager(controller, budget=budget, strict=strict)
        controller.on_mutation = history.handle_mutation
        history.reset()
        return controller, history

    return build
