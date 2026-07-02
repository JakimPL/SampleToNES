from typing import Tuple

import pytest

from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.errors import UntrackedMutationError
from sampletones_application.logic.history.manager import DEFAULT_HISTORY_BUDGET, HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager


def _history(
    *,
    strict: bool = True,
    budget: int = DEFAULT_HISTORY_BUDGET,
) -> Tuple[ProjectController, HistoryManager]:
    controller = ProjectController(ProjectManager())
    history = HistoryManager(controller, budget=budget, strict=strict)
    controller.on_mutation = history.handle_mutation
    history.reset()
    return controller, history


class TestBaseline:
    def test_reset_seeds_single_baseline(self) -> None:
        _, history = _history()

        assert len(history.entries) == 1
        assert history.cursor == 0
        assert history.can_undo is False
        assert history.can_redo is False


class TestGrouping:
    def test_single_edit_commits_one_entry(self) -> None:
        controller, history = _history()

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)

        assert len(history.entries) == 2
        assert history.cursor == 1
        assert history.can_undo is True

    def test_compound_edit_commits_one_entry(self) -> None:
        controller, history = _history()

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)
            controller.set_speed(4)

        assert len(history.entries) == 2

    def test_transaction_without_mutation_records_nothing(self) -> None:
        _, history = _history()

        with history.transaction(HistoryAction.SET_TEMPO):
            pass

        assert len(history.entries) == 1


class TestReversibility:
    def test_undo_then_redo_restores_state(self) -> None:
        controller, history = _history()
        original = controller.project.settings.tempo

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(original + 10)

        history.undo()
        assert controller.project.settings.tempo == original

        history.redo()
        assert controller.project.settings.tempo == original + 10

    def test_arbitrary_composition_reproduces_each_index(self) -> None:
        controller, history = _history()
        tempos = [110, 120, 130, 140]
        for tempo in tempos:
            with history.transaction(HistoryAction.SET_TEMPO):
                controller.set_tempo(tempo)

        # Strict verification raises on any divergence; the walk exercises many paths.
        for _ in range(3):
            history.undo()
        for _ in range(2):
            history.redo()
        history.undo()
        history.jump_to(len(history.entries) - 1)

        assert controller.project.settings.tempo == tempos[-1]

    def test_new_edit_truncates_redo_branch(self) -> None:
        controller, history = _history()

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)
        with history.transaction(HistoryAction.SET_SPEED):
            controller.set_speed(6)

        history.undo()
        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(199)

        assert history.can_redo is False
        assert controller.project.settings.tempo == 199


class TestCompleteness:
    def test_untracked_mutation_raises_under_strict(self) -> None:
        controller, _ = _history(strict=True)

        with pytest.raises(UntrackedMutationError):
            controller.set_tempo(120)

    def test_untracked_mutation_self_heals_when_lenient(self) -> None:
        controller, history = _history(strict=False)

        controller.set_tempo(120)

        assert len(history.entries) == 2
        assert history.entries[-1].action == HistoryAction.UNTRACKED


class TestBudget:
    def test_oldest_entries_are_evicted(self) -> None:
        controller, history = _history(budget=3)

        for tempo in range(100, 105):
            with history.transaction(HistoryAction.SET_TEMPO):
                controller.set_tempo(tempo)

        assert len(history.entries) == 3
        assert history.cursor == 2

    def test_navigation_after_eviction_stays_valid(self) -> None:
        controller, history = _history(budget=3)

        for tempo in range(100, 105):
            with history.transaction(HistoryAction.SET_TEMPO):
                controller.set_tempo(tempo)

        history.undo()
        history.undo()

        assert history.can_undo is False
        assert controller.project.settings.tempo == 102
