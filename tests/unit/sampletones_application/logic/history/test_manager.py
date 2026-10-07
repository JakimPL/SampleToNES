from pathlib import Path
from typing import List

import pytest

from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.errors import UntrackedMutationError
from sampletones_application.view_model.shared.history import (
    HistoryDetailRole,
    HistoryDetailSegment,
)
from tests.unit.sampletones_application.logic.history.conftest import HistoryFactory


class TestBaseline:
    def test_reset_seeds_single_baseline(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        _, history = history_factory()

        assert len(history.entries) == 1
        assert history.cursor == 0
        assert history.can_undo is False
        assert history.can_redo is False

    def test_reset_without_a_project_empties_the_stack(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()
        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)

        controller.close()
        history.reset()

        assert len(history.entries) == 0
        assert history.can_undo is False
        assert history.can_redo is False


class TestGrouping:
    def test_single_edit_commits_one_entry(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)

        assert len(history.entries) == 2
        assert history.cursor == 1
        assert history.can_undo is True

    def test_compound_edit_commits_one_entry(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)
            controller.set_speed(4)

        assert len(history.entries) == 2

    def test_transaction_without_mutation_records_nothing(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        _, history = history_factory()

        with history.transaction(HistoryAction.SET_TEMPO):
            pass

        assert len(history.entries) == 1

    def test_nested_transactions_coalesce_into_one_entry(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.ADD_SAMPLE):
            controller.set_tempo(150)
            with history.transaction(HistoryAction.SET_SPEED):
                controller.set_speed(4)
            controller.set_tempo(160)

        assert len(history.entries) == 2
        assert history.entries[-1].action is HistoryAction.ADD_SAMPLE

    def test_batched_edit_commits_one_entry(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()
        original = controller.project.settings.tempo

        with history.transaction(HistoryAction.SET_TEMPO), controller.batch():
            controller.set_tempo(150)
            controller.set_speed(4)

        assert len(history.entries) == 2

        history.undo()
        assert controller.project.settings.tempo == original


class TestRollback:
    """A gesture lands whole or not at all: one that raises leaves the project and the stack as they were."""

    def test_a_failed_gesture_restores_the_project_and_records_nothing(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()
        original = controller.project.settings.tempo

        with pytest.raises(RuntimeError), history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(170)
            raise RuntimeError("boom")

        assert controller.project.settings.tempo == original
        assert len(history.entries) == 1
        assert history.can_undo is False

    def test_a_failure_in_an_inner_scope_rolls_back_the_whole_gesture(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()
        original = (controller.project.settings.tempo, controller.project.settings.speed)

        with pytest.raises(RuntimeError), history.transaction(HistoryAction.ADD_SAMPLE):
            controller.set_tempo(170)
            with history.transaction(HistoryAction.SET_SPEED):
                controller.set_speed(4)
                raise RuntimeError("boom")

        assert (controller.project.settings.tempo, controller.project.settings.speed) == original
        assert len(history.entries) == 1

    def test_an_inner_failure_the_gesture_recovers_from_commits(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.ADD_SAMPLE):
            controller.set_tempo(170)
            with pytest.raises(RuntimeError), history.transaction(HistoryAction.SET_SPEED):
                raise RuntimeError("recovered")

        assert controller.project.settings.tempo == 170
        assert len(history.entries) == 2

    def test_a_gesture_returning_early_commits(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()

        def gesture() -> None:
            with history.transaction(HistoryAction.SET_TEMPO):
                controller.set_tempo(170)
                return

        gesture()

        assert controller.project.settings.tempo == 170
        assert len(history.entries) == 2

    def test_a_failure_before_any_mutation_reinstalls_nothing(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()
        replaced: List[bool] = []
        controller.on_project_replaced = lambda: replaced.append(True)

        with pytest.raises(RuntimeError), history.transaction(HistoryAction.SET_TEMPO):
            raise RuntimeError("boom")

        assert replaced == []

    def test_a_coalescing_run_goes_on_past_a_rollback(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()
        key = ("tempo",)
        with history.transaction(HistoryAction.SET_TEMPO, coalesce=key):
            controller.set_tempo(170)

        with pytest.raises(RuntimeError), history.transaction(HistoryAction.SET_TEMPO, coalesce=key):
            controller.set_tempo(155)
            raise RuntimeError("boom")
        with history.transaction(HistoryAction.SET_TEMPO, coalesce=key):
            controller.set_tempo(160)

        assert len(history.entries) == 2
        assert controller.project.settings.tempo == 160

    def test_a_rollback_at_the_save_point_reads_clean(
        self,
        history_factory: HistoryFactory,
        tmp_path: Path,
    ) -> None:
        controller, history = history_factory()
        controller.on_saved = history.mark_saved
        controller.save(tmp_path / "song.zip")

        with pytest.raises(RuntimeError), history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(170)
            raise RuntimeError("boom")

        assert controller.is_dirty is False

    def test_a_project_replaced_midway_rolls_nothing_back(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()

        with pytest.raises(RuntimeError), history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)
            controller.new()
            history.reset()
            controller.set_tempo(160)
            raise RuntimeError("boom")

        assert controller.project.settings.tempo == 160
        assert len(history.entries) == 1


class TestLandingEffects:
    """What a gesture does outside the project happens once the gesture lands, and goes with one rolled back."""

    def test_an_effect_runs_once_the_gesture_lands_after_its_entry(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()
        entries_seen: List[int] = []

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(170)
            history.after_landing(lambda: entries_seen.append(len(history.entries)))
            assert entries_seen == []

        assert entries_seen == [2]

    def test_an_effect_runs_at_once_between_gestures(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        _, history = history_factory()
        ran: List[str] = []

        history.after_landing(lambda: ran.append("effect"))

        assert ran == ["effect"]

    def test_a_failed_gesture_drops_its_effects(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()
        ran: List[str] = []

        with pytest.raises(RuntimeError), history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(170)
            history.after_landing(lambda: ran.append("effect"))
            raise RuntimeError("boom")

        assert ran == []

    def test_a_gesture_failing_before_any_mutation_drops_its_effects(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        _, history = history_factory()
        ran: List[str] = []

        with pytest.raises(RuntimeError), history.transaction(HistoryAction.SET_TEMPO):
            history.after_landing(lambda: ran.append("effect"))
            raise RuntimeError("boom")

        assert ran == []

    def test_an_inner_scope_effect_waits_for_the_outermost(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()
        ran: List[str] = []

        with history.transaction(HistoryAction.ADD_SAMPLE):
            with history.transaction(HistoryAction.SET_TEMPO):
                controller.set_tempo(170)
                history.after_landing(lambda: ran.append("effect"))
            assert ran == []

        assert ran == ["effect"]

    def test_a_gesture_changing_nothing_runs_its_effects(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        _, history = history_factory()
        ran: List[str] = []

        with history.transaction(HistoryAction.CUT_BLOCK):
            history.after_landing(lambda: ran.append("effect"))

        assert ran == ["effect"]
        assert len(history.entries) == 1

    def test_effects_run_in_the_order_they_were_handed_in(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()
        ran: List[str] = []

        with history.transaction(HistoryAction.SET_TEMPO):
            history.after_landing(lambda: ran.append("first"))
            controller.set_tempo(170)
            history.after_landing(lambda: ran.append("second"))

        assert ran == ["first", "second"]

    def test_an_effect_handed_in_by_a_rollback_runs_at_once(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        """The reinstall runs between gestures, so what it gives rise to follows the project it puts back."""
        controller, history = history_factory()
        ran: List[str] = []
        controller.on_project_replaced = lambda: history.after_landing(lambda: ran.append("effect"))

        with pytest.raises(RuntimeError), history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(170)
            raise RuntimeError("boom")

        assert ran == ["effect"]


class TestCoalescing:
    def test_same_action_and_target_replaces_top_entry(
        self,
        history_factory: HistoryFactory,
    ) -> None:
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

    def test_different_action_appends(
        self,
        history_factory: HistoryFactory,
    ) -> None:
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

    def test_intervening_gesture_breaks_run(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.SET_TEMPO, coalesce=()):
            controller.set_tempo(150)

        with history.transaction(HistoryAction.SET_SPEED):
            controller.set_speed(4)

        with history.transaction(HistoryAction.SET_TEMPO, coalesce=()):
            controller.set_tempo(160)

        assert len(history.entries) == 4

    def test_empty_gesture_keeps_run(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.SET_TEMPO, coalesce=()):
            controller.set_tempo(150)

        with history.transaction(HistoryAction.SET_SPEED):
            pass

        with history.transaction(HistoryAction.SET_TEMPO, coalesce=()):
            controller.set_tempo(160)

        assert len(history.entries) == 2

    def test_replacement_refreshes_detail(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()
        first = (HistoryDetailSegment(text="150", role=HistoryDetailRole.VALUE),)
        second = (HistoryDetailSegment(text="160", role=HistoryDetailRole.VALUE),)

        with history.transaction(
            HistoryAction.SET_TEMPO,
            detail=first,
            coalesce=(),
        ):
            controller.set_tempo(150)

        with history.transaction(
            HistoryAction.SET_TEMPO,
            detail=second,
            coalesce=(),
        ):
            controller.set_tempo(160)

        assert history.entries[-1].detail == second


class TestReversibility:
    def test_undo_then_redo_restores_state(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()
        original = controller.project.settings.tempo

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(original + 10)

        history.undo()
        assert controller.project.settings.tempo == original

        history.redo()
        assert controller.project.settings.tempo == original + 10

    def test_arbitrary_composition_reproduces_each_index(
        self,
        history_factory: HistoryFactory,
    ) -> None:
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

    def test_new_edit_truncates_redo_branch(
        self,
        history_factory: HistoryFactory,
    ) -> None:
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

    def test_jump_to_out_of_range_or_current_is_ignored(
        self,
        history_factory: HistoryFactory,
    ) -> None:
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


class TestSavedCursor:
    def test_undo_to_clean_baseline_clears_dirty(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)

        assert controller.is_dirty is True

        history.undo()
        assert controller.is_dirty is False

    def test_undo_to_save_point_clears_dirty(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)

        history.mark_saved()
        with history.transaction(HistoryAction.SET_SPEED):
            controller.set_speed(4)

        assert controller.is_dirty is True

        history.undo()
        assert controller.is_dirty is False

        history.redo()
        assert controller.is_dirty is True

    def test_save_hook_marks_the_current_cursor(
        self,
        history_factory: HistoryFactory,
        tmp_path: Path,
    ) -> None:
        controller, history = history_factory()
        controller.on_saved = history.mark_saved

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)
        controller.save(tmp_path / "song.zip")
        with history.transaction(HistoryAction.SET_SPEED):
            controller.set_speed(4)

        history.undo()
        assert controller.is_dirty is False

    def test_truncating_the_saved_branch_keeps_dirty(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)
        history.mark_saved()
        history.undo()
        with history.transaction(HistoryAction.SET_SPEED):
            controller.set_speed(4)

        history.undo()
        assert controller.is_dirty is True
        history.redo()
        assert controller.is_dirty is True

    def test_eviction_shifts_the_saved_cursor(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory(budget=3)

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(100)

        history.mark_saved()
        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(101)

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(102)

        history.undo()
        history.undo()

        assert controller.project.settings.tempo == 100
        assert controller.is_dirty is False

    def test_evicting_the_saved_entry_keeps_dirty(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory(budget=2)

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(100)

        history.mark_saved()
        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(101)

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(102)

        history.undo()
        assert controller.is_dirty is True

    def test_coalescing_never_replaces_the_saved_entry(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory()

        with history.transaction(HistoryAction.SET_TEMPO, coalesce=()):
            controller.set_tempo(150)
        history.mark_saved()
        with history.transaction(HistoryAction.SET_TEMPO, coalesce=()):
            controller.set_tempo(160)

        assert len(history.entries) == 3

        history.undo()
        assert controller.project.settings.tempo == 150
        assert controller.is_dirty is False


class TestCompleteness:
    def test_untracked_mutation_raises_under_strict(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, _ = history_factory(strict=True)

        with pytest.raises(UntrackedMutationError):
            controller.set_tempo(120)

    def test_batched_mutation_outside_a_transaction_raises_under_strict(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        """A batch defers the notifications a gesture raises, never the mutations it records."""
        controller, _ = history_factory(strict=True)

        with pytest.raises(UntrackedMutationError), controller.batch():
            controller.set_tempo(120)

    def test_untracked_mutation_self_heals_when_lenient(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory(strict=False)

        controller.set_tempo(120)

        assert len(history.entries) == 2
        assert history.entries[-1].action == HistoryAction.UNTRACKED


class TestBudget:
    def test_oldest_entries_are_evicted(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory(budget=3)

        for tempo in range(100, 105):
            with history.transaction(HistoryAction.SET_TEMPO):
                controller.set_tempo(tempo)

        assert len(history.entries) == 3
        assert history.cursor == 2

    def test_navigation_after_eviction_stays_valid(
        self,
        history_factory: HistoryFactory,
    ) -> None:
        controller, history = history_factory(budget=3)

        for tempo in range(100, 105):
            with history.transaction(HistoryAction.SET_TEMPO):
                controller.set_tempo(tempo)

        history.undo()
        history.undo()

        assert history.can_undo is False
        assert controller.project.settings.tempo == 102
