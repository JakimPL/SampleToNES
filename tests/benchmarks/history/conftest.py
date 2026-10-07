from typing import Final

import pytest

from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from tests.suite.history.wiring import wired_history

HISTORY_BUDGET: Final[int] = 500


@pytest.fixture(name="controller")
def controller_fixture() -> ProjectController:
    """A controller over a new project, which a module arranges before its history starts."""
    controller = ProjectController(ProjectManager())
    controller.new()
    return controller


@pytest.fixture(name="history")
def history_fixture(arranged: ProjectController) -> HistoryManager:
    """A history whose first entry is the arranged project.

    The history records the entries alone, as a user build's does, so a reading is what storing an
    entry costs. The fingerprint a strict deployment adds to each commit is a cost of its own.
    """
    history = wired_history(arranged, budget=HISTORY_BUDGET, strict=False)
    history.reset()
    return history
