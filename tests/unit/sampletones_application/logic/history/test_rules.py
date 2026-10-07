from dataclasses import dataclass
from pathlib import Path
from typing import Callable, ClassVar, Dict, Final, Optional, Protocol, Sequence, Tuple, Union

import pytest

from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.transaction import CoalesceKey
from sampletones_application.logic.project.controller import ProjectController
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.unit.sampletones_application.logic.history.conftest import AuditedHistory, AuditFactory

TEMPO_KEY: Final[CoalesceKey] = ("tempo",)
OTHER_KEY: Final[CoalesceKey] = ("other",)
SAVED_NAME: Final[str] = "saved.stp"
TIGHT_BUDGET: Final[int] = 3
ROOMY_BUDGET: Final[int] = 20

INITIAL: Final = HistoryAction.INITIAL
TEMPO: Final = HistoryAction.SET_TEMPO
SPEED: Final = HistoryAction.SET_SPEED
PROPERTIES: Final = HistoryAction.EDIT_PROJECT_PROPERTIES


def _raise_tempo(controller: ProjectController) -> None:
    controller.set_tempo(controller.project.settings.tempo + 1)


def _toggle_speed(controller: ProjectController) -> None:
    controller.set_speed(controller.project.settings.speed % 2 + 5)


def _retitle(controller: ProjectController) -> None:
    controller.set_title(f"{controller.project.info.title}!")


EDITS: Final[Dict[HistoryAction, Callable[[ProjectController], None]]] = {
    TEMPO: _raise_tempo,
    SPEED: _toggle_speed,
    PROPERTIES: _retitle,
}


class Step(Protocol):
    def run(
        self,
        audited: AuditedHistory,
        saved: Path,
    ) -> None: ...


@dataclass(frozen=True)
class Commit:
    """One gesture of ``action`` on the target ``key`` names, checked by the audit."""

    action: HistoryAction
    key: Optional[CoalesceKey]

    def run(
        self,
        audited: AuditedHistory,
        saved: Path,
    ) -> None:
        def gesture() -> None:
            with audited.history.transaction(self.action, coalesce=self.key):
                EDITS[self.action](audited.controller)

        audited.audit.perform(gesture, action=self.action, target=self.key)


@dataclass(frozen=True)
class Undo:
    def run(
        self,
        audited: AuditedHistory,
        saved: Path,
    ) -> None:
        audited.audit.undo()


@dataclass(frozen=True)
class Redo:
    def run(
        self,
        audited: AuditedHistory,
        saved: Path,
    ) -> None:
        audited.audit.redo()


@dataclass(frozen=True)
class Jump:
    index: int

    def run(
        self,
        audited: AuditedHistory,
        saved: Path,
    ) -> None:
        audited.audit.jump_to(self.index)


@dataclass(frozen=True)
class Save:
    def run(
        self,
        audited: AuditedHistory,
        saved: Path,
    ) -> None:
        audited.audit.save(lambda: audited.controller.save(saved))


AnyStep = Union[Commit, Undo, Redo, Jump, Save]


def _walk(
    audit_factory: AuditFactory,
    tmp_path: Path,
    steps: Sequence[AnyStep],
    *,
    budget: int,
) -> AuditedHistory:
    audited = audit_factory(budget=budget)
    for step in steps:
        step.run(audited, tmp_path / SAVED_NAME)

    return audited


def _assert_stack(
    audited: AuditedHistory,
    *,
    actions: Tuple[HistoryAction, ...],
    cursor: int,
    dirty: bool,
) -> None:
    assert tuple(entry.action for entry in audited.history.entries) == actions
    assert audited.history.cursor == cursor
    assert audited.controller.is_dirty is dirty


class TestCoalescing(BaseTestSuite):
    """Consecutive gestures of one action on one target make one entry, until something ends the run."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        steps: Tuple[AnyStep, ...]
        expected: Tuple[HistoryAction, ...]
        cursor: int

    test_cases: ClassVar[Sequence[TestCase]] = [
        TestCase(
            label="one target twice runs together",
            steps=(Commit(TEMPO, TEMPO_KEY), Commit(TEMPO, TEMPO_KEY)),
            expected=(INITIAL, TEMPO),
            cursor=1,
        ),
        TestCase(
            label="one target three times runs together",
            steps=(Commit(TEMPO, TEMPO_KEY), Commit(TEMPO, TEMPO_KEY), Commit(TEMPO, TEMPO_KEY)),
            expected=(INITIAL, TEMPO),
            cursor=1,
        ),
        TestCase(
            label="two targets stay apart",
            steps=(Commit(TEMPO, TEMPO_KEY), Commit(TEMPO, OTHER_KEY)),
            expected=(INITIAL, TEMPO, TEMPO),
            cursor=2,
        ),
        TestCase(
            label="two actions on one target stay apart",
            steps=(Commit(TEMPO, TEMPO_KEY), Commit(SPEED, TEMPO_KEY)),
            expected=(INITIAL, TEMPO, SPEED),
            cursor=2,
        ),
        TestCase(
            label="a gesture naming no target never runs",
            steps=(Commit(PROPERTIES, None), Commit(PROPERTIES, None)),
            expected=(INITIAL, PROPERTIES, PROPERTIES),
            cursor=2,
        ),
        TestCase(
            label="another gesture between ends the run",
            steps=(Commit(TEMPO, TEMPO_KEY), Commit(SPEED, OTHER_KEY), Commit(TEMPO, TEMPO_KEY)),
            expected=(INITIAL, TEMPO, SPEED, TEMPO),
            cursor=3,
        ),
        TestCase(
            label="an undo and a redo between end the run",
            steps=(Commit(TEMPO, TEMPO_KEY), Undo(), Redo(), Commit(TEMPO, TEMPO_KEY)),
            expected=(INITIAL, TEMPO, TEMPO),
            cursor=2,
        ),
        TestCase(
            label="a jump away and back ends the run",
            steps=(Commit(TEMPO, TEMPO_KEY), Jump(0), Jump(1), Commit(TEMPO, TEMPO_KEY)),
            expected=(INITIAL, TEMPO, TEMPO),
            cursor=2,
        ),
        TestCase(
            label="a jump onto the cursor keeps the run",
            steps=(Commit(TEMPO, TEMPO_KEY), Jump(1), Commit(TEMPO, TEMPO_KEY)),
            expected=(INITIAL, TEMPO),
            cursor=1,
        ),
        TestCase(
            label="an undo at the start keeps nothing from running",
            steps=(Undo(), Commit(TEMPO, TEMPO_KEY), Commit(TEMPO, TEMPO_KEY)),
            expected=(INITIAL, TEMPO),
            cursor=1,
        ),
        TestCase(
            label="a save between ends the run",
            steps=(Commit(TEMPO, TEMPO_KEY), Save(), Commit(TEMPO, TEMPO_KEY)),
            expected=(INITIAL, TEMPO, TEMPO),
            cursor=2,
        ),
        TestCase(
            label="a run starts again past the save point",
            steps=(Commit(TEMPO, TEMPO_KEY), Save(), Commit(TEMPO, TEMPO_KEY), Commit(TEMPO, TEMPO_KEY)),
            expected=(INITIAL, TEMPO, TEMPO),
            cursor=2,
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_entries(
        self,
        test_case: TestCase,
        audit_factory: AuditFactory,
        tmp_path: Path,
    ) -> None:
        audited = _walk(audit_factory, tmp_path, test_case.steps, budget=ROOMY_BUDGET)

        assert tuple(entry.action for entry in audited.history.entries) == test_case.expected
        assert audited.history.cursor == test_case.cursor


class TestSavePoint(BaseTestSuite):
    """The entry last saved reads clean whenever the cursor stands on it, until it leaves the stack."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        steps: Tuple[AnyStep, ...]
        budget: int
        expected: Tuple[HistoryAction, ...]
        cursor: int
        dirty: bool

    test_cases: ClassVar[Sequence[TestCase]] = [
        TestCase(
            label="an opened project starts clean",
            steps=(),
            budget=ROOMY_BUDGET,
            expected=(INITIAL,),
            cursor=0,
            dirty=False,
        ),
        TestCase(
            label="an edit leaves the save point",
            steps=(Commit(TEMPO, TEMPO_KEY),),
            budget=ROOMY_BUDGET,
            expected=(INITIAL, TEMPO),
            cursor=1,
            dirty=True,
        ),
        TestCase(
            label="an undo back onto the opened state is clean",
            steps=(Commit(TEMPO, TEMPO_KEY), Undo()),
            budget=ROOMY_BUDGET,
            expected=(INITIAL, TEMPO),
            cursor=0,
            dirty=False,
        ),
        TestCase(
            label="an undo past a save is dirty",
            steps=(Commit(TEMPO, TEMPO_KEY), Save(), Undo()),
            budget=ROOMY_BUDGET,
            expected=(INITIAL, TEMPO),
            cursor=0,
            dirty=True,
        ),
        TestCase(
            label="a redo back onto a save is clean",
            steps=(Commit(TEMPO, TEMPO_KEY), Save(), Undo(), Redo()),
            budget=ROOMY_BUDGET,
            expected=(INITIAL, TEMPO),
            cursor=1,
            dirty=False,
        ),
        TestCase(
            label="a jump onto a save is clean",
            steps=(Commit(TEMPO, TEMPO_KEY), Save(), Commit(SPEED, OTHER_KEY), Jump(0), Jump(1)),
            budget=ROOMY_BUDGET,
            expected=(INITIAL, TEMPO, SPEED),
            cursor=1,
            dirty=False,
        ),
        TestCase(
            label="a commit over the saved branch leaves nothing clean",
            steps=(Commit(TEMPO, TEMPO_KEY), Save(), Undo(), Commit(SPEED, OTHER_KEY), Undo()),
            budget=ROOMY_BUDGET,
            expected=(INITIAL, SPEED),
            cursor=0,
            dirty=True,
        ),
        TestCase(
            label="a run past the save point keeps the saved entry",
            steps=(Commit(TEMPO, TEMPO_KEY), Save(), Commit(TEMPO, TEMPO_KEY), Commit(TEMPO, TEMPO_KEY), Undo()),
            budget=ROOMY_BUDGET,
            expected=(INITIAL, TEMPO, TEMPO),
            cursor=1,
            dirty=False,
        ),
        TestCase(
            label="eviction moves the save point with its entry",
            steps=(
                Commit(TEMPO, None),
                Save(),
                Commit(SPEED, None),
                Commit(PROPERTIES, None),
                Undo(),
                Undo(),
            ),
            budget=TIGHT_BUDGET,
            expected=(TEMPO, SPEED, PROPERTIES),
            cursor=0,
            dirty=False,
        ),
        TestCase(
            label="eviction of the saved entry leaves nothing clean",
            steps=(
                Commit(TEMPO, None),
                Commit(SPEED, None),
                Commit(PROPERTIES, None),
                Undo(),
                Undo(),
            ),
            budget=TIGHT_BUDGET,
            expected=(TEMPO, SPEED, PROPERTIES),
            cursor=0,
            dirty=True,
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_dirty_state(
        self,
        test_case: TestCase,
        audit_factory: AuditFactory,
        tmp_path: Path,
    ) -> None:
        audited = _walk(audit_factory, tmp_path, test_case.steps, budget=test_case.budget)

        _assert_stack(
            audited,
            actions=test_case.expected,
            cursor=test_case.cursor,
            dirty=test_case.dirty,
        )


class TestStackShape(BaseTestSuite):
    """A commit drops the redo branch, and the budget drops the oldest entries."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        steps: Tuple[AnyStep, ...]
        budget: int
        expected: Tuple[HistoryAction, ...]
        cursor: int

    test_cases: ClassVar[Sequence[TestCase]] = [
        TestCase(
            label="a commit after two undos drops both redone entries",
            steps=(
                Commit(TEMPO, None),
                Commit(SPEED, None),
                Commit(PROPERTIES, None),
                Undo(),
                Undo(),
                Commit(SPEED, None),
            ),
            budget=ROOMY_BUDGET,
            expected=(INITIAL, TEMPO, SPEED),
            cursor=2,
        ),
        TestCase(
            label="a commit after a jump to the start keeps only the baseline",
            steps=(Commit(TEMPO, None), Commit(SPEED, None), Jump(0), Commit(PROPERTIES, None)),
            budget=ROOMY_BUDGET,
            expected=(INITIAL, PROPERTIES),
            cursor=1,
        ),
        TestCase(
            label="undos and redos alone keep every entry",
            steps=(Commit(TEMPO, None), Commit(SPEED, None), Undo(), Undo(), Redo(), Redo(), Redo()),
            budget=ROOMY_BUDGET,
            expected=(INITIAL, TEMPO, SPEED),
            cursor=2,
        ),
        TestCase(
            label="the budget drops the oldest entries",
            steps=(Commit(TEMPO, None), Commit(SPEED, None), Commit(PROPERTIES, None), Commit(TEMPO, None)),
            budget=TIGHT_BUDGET,
            expected=(SPEED, PROPERTIES, TEMPO),
            cursor=2,
        ),
        TestCase(
            label="a stack at its budget keeps every entry",
            steps=(Commit(TEMPO, None), Commit(SPEED, None)),
            budget=TIGHT_BUDGET,
            expected=(INITIAL, TEMPO, SPEED),
            cursor=2,
        ),
        TestCase(
            label="a run at the budget replaces the top and drops nothing",
            steps=(Commit(TEMPO, None), Commit(SPEED, TEMPO_KEY), Commit(SPEED, TEMPO_KEY)),
            budget=TIGHT_BUDGET,
            expected=(INITIAL, TEMPO, SPEED),
            cursor=2,
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_entries(
        self,
        test_case: TestCase,
        audit_factory: AuditFactory,
        tmp_path: Path,
    ) -> None:
        audited = _walk(audit_factory, tmp_path, test_case.steps, budget=test_case.budget)

        assert tuple(entry.action for entry in audited.history.entries) == test_case.expected
        assert audited.history.cursor == test_case.cursor

    def test_every_entry_the_budget_keeps_restores_its_state(
        self,
        audit_factory: AuditFactory,
        tmp_path: Path,
    ) -> None:
        audited = _walk(
            audit_factory,
            tmp_path,
            (Commit(TEMPO, None), Commit(SPEED, None), Commit(PROPERTIES, None), Commit(TEMPO, None)),
            budget=TIGHT_BUDGET,
        )

        audited.audit.walk()
