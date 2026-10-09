from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol, Tuple

import pytest

from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from tests.suite.history.audit import HistoryAudit, immediately
from tests.suite.history.projects import every_part_file
from tests.suite.history.wiring import wired_history

DEFAULT_HISTORY_BUDGET: Final[int] = 10
AUDIT_BUDGET: Final[int] = 20


class HistoryFactory(Protocol):
    def __call__(
        self,
        *,
        strict: bool = True,
        budget: int = DEFAULT_HISTORY_BUDGET,
    ) -> Tuple[ProjectController, HistoryManager]: ...


@dataclass(frozen=True)
class AuditedHistory:
    """A strict history over the every-part project, with the audit holding it to its rules."""

    controller: ProjectController
    history: HistoryManager
    audit: HistoryAudit


class AuditFactory(Protocol):
    def __call__(self, *, budget: int = AUDIT_BUDGET) -> AuditedHistory: ...


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
        history = wired_history(controller, budget=budget, strict=strict)
        controller.new()
        history.reset()
        return controller, history

    return build


@pytest.fixture
def audit_factory(every_part_file: Path) -> AuditFactory:
    """Opens the every-part project under a strict history of ``budget`` entries and audits it."""

    def build(*, budget: int = AUDIT_BUDGET) -> AuditedHistory:
        controller = ProjectController(ProjectManager())
        history = wired_history(controller, budget=budget, strict=True)
        controller.load(every_part_file)
        history.reset()
        audit = HistoryAudit(
            controller,
            history,
            budget=budget,
            doors=history,
            settle=immediately,
            observers=(),
        )
        return AuditedHistory(controller=controller, history=history, audit=audit)

    return build


@pytest.fixture
def audited(audit_factory: AuditFactory) -> AuditedHistory:
    return audit_factory()
