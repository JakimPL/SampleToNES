from typing import List

import pytest

from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.errors import UntrackedMutationError
from sampletones_application.view_model.sequencer.history import HistoryDetailRole, HistoryDetailSegment
from tests.unit.sampletones_application.logic.history.conftest import HistoryFactory


class TestBaseline:
    def test_reset_seeds_single_baseline(self, history_factory: HistoryFactory) -> None:
        _, history = history_factory()

        assert len(history.entries) == 1
        assert history.cursor == 0
        assert history.can_undo is False
        assert history.can_redo is False


class TestGrouping:
    def test_single_edit_commits_one_entry(self, history_factory: HistoryFactory) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)

        assert len(history.entries) == 2
        assert history.cursor == 1
        assert history.can_undo is True

    def test_compound_edit_commits_one_entry(self, history_factory: HistoryFactory) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)
            controller.set_speed(4)

        assert len(history.entries) == 2

    def test_transaction_without_mutation_records_nothing(self, history_factory: HistoryFactory) -> None:
        _, history = history_factory()

        with history.transaction(HistoryAction.SET_TEMPO):
            pass

        assert len(history.entries) == 1

    def test_nested_transactions_coalesce_into_one_entry(self, history_factory: HistoryFactory) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.ADD_SAMPLE):
            controller.set_tempo(150)
            with history.transaction(HistoryAction.SET_SPEED):
                controller.set_speed(4)
            controller.set_tempo(160)

        assert len(history.entries) == 2
        assert history.entries[-1].action is HistoryAction.ADD_SAMPLE

    def test_exception_inside_transaction_commits_partial_gesture(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()
        original = controller.project.settings.tempo

        with pytest.raises(RuntimeError):
            with history.transaction(HistoryAction.SET_TEMPO):
                controller.set_tempo(150)
                raise RuntimeError("boom")

        assert len(history.entries) == 2
        assert controller.project.settings.tempo == 150

        history.undo()
        assert controller.project.settings.tempo == original


class TestCoalescing:
    def test_same_action_and_target_replaces_top_entry(self, history_factory: HistoryFactory) -> None:
        controller, history = history_factory()
        original = controller.project.settings.tempo

        with history.transaction(HistoryAction.SET_TEMPO, coalesce=()):
            controller.set_tempo(150)
        with history.transaction(HistoryAction.SET_TEMPO, coalesce=()):
            controller.set_tempo(160)

        assert len(history.entries) == 2
        assert controller.project.settings.tempo == 160

        history.undo()
        assert controller.project.settings.tempo == original

        history.redo()
        assert controller.project.settings.tempo == 160

    def test_different_target_appends(self, history_factory: HistoryFactory) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.EDIT_ROW, coalesce=(0, "pulse1", 3)):
            controller.set_tempo(150)
        with history.transaction(HistoryAction.EDIT_ROW, coalesce=(0, "pulse1", 4)):
            controller.set_tempo(160)

        assert len(history.entries) == 3

    def test_different_action_appends(self, history_factory: HistoryFactory) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.SET_TEMPO, coalesce=()):
            controller.set_tempo(150)
        with history.transaction(HistoryAction.SET_SPEED, coalesce=()):
            controller.set_speed(4)

        assert len(history.entries) == 3

    def test_restore_breaks_run(self, history_factory: HistoryFactory) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.SET_TEMPO, coalesce=()):
            controller.set_tempo(150)
        history.undo()
        history.redo()
        with history.transaction(HistoryAction.SET_TEMPO, coalesce=()):
            controller.set_tempo(160)

        assert len(history.entries) == 3
        assert controller.project.settings.tempo == 160

    def test_intervening_gesture_breaks_run(self, history_factory: HistoryFactory) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.SET_TEMPO, coalesce=()):
            controller.set_tempo(150)
        with history.transaction(HistoryAction.SET_SPEED):
            controller.set_speed(4)
        with history.transaction(HistoryAction.SET_TEMPO, coalesce=()):
            controller.set_tempo(160)

        assert len(history.entries) == 4

    def test_empty_gesture_keeps_run(self, history_factory: HistoryFactory) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.SET_TEMPO, coalesce=()):
            controller.set_tempo(150)
        with history.transaction(HistoryAction.SET_SPEED):
            pass
        with history.transaction(HistoryAction.SET_TEMPO, coalesce=()):
            controller.set_tempo(160)

        assert len(history.entries) == 2

    def test_replacement_refreshes_detail(self, history_factory: HistoryFactory) -> None:
        controller, history = history_factory()
        first = (HistoryDetailSegment(text="150", role=HistoryDetailRole.VALUE),)
        second = (HistoryDetailSegment(text="160", role=HistoryDetailRole.VALUE),)

        with history.transaction(HistoryAction.SET_TEMPO, detail=first, coalesce=()):
            controller.set_tempo(150)
        with history.transaction(HistoryAction.SET_TEMPO, detail=second, coalesce=()):
            controller.set_tempo(160)

        assert history.entries[-1].detail == second


class TestReversibility:
    def test_undo_then_redo_restores_state(self, history_factory: HistoryFactory) -> None:
        controller, history = history_factory()
        original = controller.project.settings.tempo

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(original + 10)

        history.undo()
        assert controller.project.settings.tempo == original

        history.redo()
        assert controller.project.settings.tempo == original + 10

    def test_arbitrary_composition_reproduces_each_index(self, history_factory: HistoryFactory) -> None:
        controller, history = history_factory()
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

    def test_new_edit_truncates_redo_branch(self, history_factory: HistoryFactory) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)
        with history.transaction(HistoryAction.SET_SPEED):
            controller.set_speed(6)

        history.undo()
        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(199)

        assert history.can_redo is False
        assert controller.project.settings.tempo == 199

    def test_jump_to_out_of_range_or_current_is_ignored(self, history_factory: HistoryFactory) -> None:
        controller, history = history_factory()
        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)
        notifications: List[int] = []
        history.on_history_changed = lambda: notifications.append(history.cursor)

        history.jump_to(-1)
        history.jump_to(len(history.entries))
        history.jump_to(history.cursor)

        assert history.cursor == 1
        assert controller.project.settings.tempo == 150
        assert notifications == []


class TestCompleteness:
    def test_untracked_mutation_raises_under_strict(self, history_factory: HistoryFactory) -> None:
        controller, _ = history_factory(strict=True)

        with pytest.raises(UntrackedMutationError):
            controller.set_tempo(120)

    def test_untracked_mutation_self_heals_when_lenient(self, history_factory: HistoryFactory) -> None:
        controller, history = history_factory(strict=False)

        controller.set_tempo(120)

        assert len(history.entries) == 2
        assert history.entries[-1].action == HistoryAction.UNTRACKED


class TestBudget:
    def test_oldest_entries_are_evicted(self, history_factory: HistoryFactory) -> None:
        controller, history = history_factory(budget=3)

        for tempo in range(100, 105):
            with history.transaction(HistoryAction.SET_TEMPO):
                controller.set_tempo(tempo)

        assert len(history.entries) == 3
        assert history.cursor == 2

    def test_navigation_after_eviction_stays_valid(self, history_factory: HistoryFactory) -> None:
        controller, history = history_factory(budget=3)

        for tempo in range(100, 105):
            with history.transaction(HistoryAction.SET_TEMPO):
                controller.set_tempo(tempo)

        history.undo()
        history.undo()

        assert history.can_undo is False
        assert controller.project.settings.tempo == 102
