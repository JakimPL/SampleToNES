from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.coordinators.sequencer import SequencerTabCoordinator
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.history.snapshot import snapshot_project
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.view_model.shared.history import HistoryDetailRole, HistoryDetailSegment
from sampletones_core.constants.enums import GeneratorName


@pytest.fixture
def coordinator() -> SequencerTabCoordinator:
    """A coordinator with only the collaborators ``import_reconstruction`` touches.

    The full constructor builds the sequencer's GUI subtree (themes, fonts, synthesiser), which
    is out of scope here; only the import orchestration is under test. Defaults to an open project
    with samples and a matching reconstruction frequency (60 Hz); individual tests override.
    """
    instance = object.__new__(SequencerTabCoordinator)
    instance._history = MagicMock()
    instance._history_detail = MagicMock()
    instance._project_controller = MagicMock()
    instance._project_controller.is_open = True
    instance._project_controller.has_samples = True
    instance._sequencer_browser_logic = MagicMock()
    instance._sequencer_browser_logic.load_reconstruction.return_value.config.nes_frequency = 60
    instance._sequencer_grid_logic = MagicMock()
    instance._sequencer_grid_logic.settings.nes_frequency = 60
    instance._dialogs = MagicMock()
    instance._on_tab_switch = MagicMock()
    instance._msg_no_project = "no project"
    instance._ttl_no_project = "No project open"
    instance._ttl_frequency_mismatch = "Different NES frequency"
    instance._msg_frequency_mismatch = "recon {reconstruction} vs project {project}"
    instance._lbl_add_anyway = "Add anyway"
    return instance


@pytest.fixture
def samples_coordinator() -> SequencerTabCoordinator:
    """A coordinator with only the collaborators the samples-menu handlers touch."""
    instance = object.__new__(SequencerTabCoordinator)
    instance._history = MagicMock()
    instance._history_detail = MagicMock()
    instance._sequencer_samples_logic = MagicMock()
    instance._dialogs = MagicMock()
    instance._ttl_remove_sample = "Remove sample"
    instance._msg_remove_sample = "Remove {name}?"
    instance._lbl_remove_sample = "Remove"
    return instance


class TestRemoveSample:
    def test_unused_sample_is_removed_without_confirmation(
        self,
        samples_coordinator: SequencerTabCoordinator,
    ) -> None:
        samples_coordinator._sequencer_samples_logic.is_sample_used.return_value = False

        samples_coordinator._remove_sample("abc")

        samples_coordinator._sequencer_samples_logic.remove_sample.assert_called_once_with("abc")
        samples_coordinator._dialogs.show_confirmation.assert_not_called()

    def test_used_sample_prompts_confirmation_before_removing(
        self,
        samples_coordinator: SequencerTabCoordinator,
    ) -> None:
        logic = samples_coordinator._sequencer_samples_logic
        logic.is_sample_used.return_value = True
        logic.sample_name.return_value = "lead"

        samples_coordinator._remove_sample("abc")

        samples_coordinator._dialogs.show_confirmation.assert_called_once()
        logic.remove_sample.assert_not_called()

        confirmation = samples_coordinator._dialogs.show_confirmation.call_args.kwargs
        assert confirmation["message"] == "Remove lead?"

        confirmation["on_confirm"]()
        logic.remove_sample.assert_called_once_with("abc")


class TestSubmitRename:
    def test_submit_rename_trims_whitespace(
        self,
        samples_coordinator: SequencerTabCoordinator,
    ) -> None:
        samples_coordinator._submit_rename("abc", "  bass  ")

        samples_coordinator._sequencer_samples_logic.rename_sample.assert_called_once_with("abc", "bass")

    def test_submit_rename_ignores_blank_name(
        self,
        samples_coordinator: SequencerTabCoordinator,
    ) -> None:
        samples_coordinator._submit_rename("abc", "   ")

        samples_coordinator._sequencer_samples_logic.rename_sample.assert_not_called()


@pytest.fixture
def nes_frequency_coordinator() -> SequencerTabCoordinator:
    """A coordinator with only the collaborators the NES-frequency change handler touches."""
    instance = object.__new__(SequencerTabCoordinator)
    instance._history = MagicMock()
    instance._history_detail = MagicMock()
    instance._sequencer_grid_logic = MagicMock()
    instance._sequencer_grid_logic.settings.nes_frequency = 60
    instance._project_controller = MagicMock()
    instance._project_controller.has_samples = True
    instance._dialogs = MagicMock()
    instance._nes_frequency_change_acknowledged = False
    instance._ttl_change_nes_frequency = "Change NES frequency"
    instance._msg_change_nes_frequency = "Re-times samples. Continue?"
    instance._lbl_change_nes_frequency = "Change"
    instance._lbl_dont_ask_again = "Don't ask again"
    return instance


class TestRequestNesFrequencyChange:
    def test_unchanged_value_does_nothing(
        self,
        nes_frequency_coordinator: SequencerTabCoordinator,
    ) -> None:
        nes_frequency_coordinator._request_nes_frequency_change(60)

        nes_frequency_coordinator._sequencer_grid_logic.set_nes_frequency.assert_not_called()
        nes_frequency_coordinator._dialogs.show_confirmation.assert_not_called()

    def test_applies_without_confirmation_when_no_samples(
        self,
        nes_frequency_coordinator: SequencerTabCoordinator,
    ) -> None:
        nes_frequency_coordinator._project_controller.has_samples = False

        nes_frequency_coordinator._request_nes_frequency_change(30)

        nes_frequency_coordinator._sequencer_grid_logic.set_nes_frequency.assert_called_once_with(30)
        nes_frequency_coordinator._dialogs.show_confirmation.assert_not_called()

    def test_applies_without_confirmation_once_acknowledged(
        self,
        nes_frequency_coordinator: SequencerTabCoordinator,
    ) -> None:
        nes_frequency_coordinator._nes_frequency_change_acknowledged = True

        nes_frequency_coordinator._request_nes_frequency_change(30)

        nes_frequency_coordinator._sequencer_grid_logic.set_nes_frequency.assert_called_once_with(30)
        nes_frequency_coordinator._dialogs.show_confirmation.assert_not_called()

    def test_prompts_before_applying_when_samples_exist(
        self,
        nes_frequency_coordinator: SequencerTabCoordinator,
    ) -> None:
        nes_frequency_coordinator._request_nes_frequency_change(30)

        nes_frequency_coordinator._dialogs.show_confirmation.assert_called_once()
        nes_frequency_coordinator._sequencer_grid_logic.set_nes_frequency.assert_not_called()

        confirmation = nes_frequency_coordinator._dialogs.show_confirmation.call_args.kwargs
        confirmation["on_confirm"]()
        nes_frequency_coordinator._sequencer_grid_logic.set_nes_frequency.assert_called_once_with(30)

    def test_opt_out_acknowledges_for_the_session(
        self,
        nes_frequency_coordinator: SequencerTabCoordinator,
    ) -> None:
        nes_frequency_coordinator._request_nes_frequency_change(30)

        confirmation = nes_frequency_coordinator._dialogs.show_confirmation.call_args.kwargs
        confirmation["on_opt_out"]()

        assert nes_frequency_coordinator._nes_frequency_change_acknowledged is True

    def test_cancel_restores_the_field(
        self,
        nes_frequency_coordinator: SequencerTabCoordinator,
    ) -> None:
        nes_frequency_coordinator._request_nes_frequency_change(30)

        confirmation = nes_frequency_coordinator._dialogs.show_confirmation.call_args.kwargs
        confirmation["on_cancel"]()

        nes_frequency_coordinator._sequencer_grid_logic.push_settings.assert_called_once()


@pytest.fixture
def playback_coordinator() -> SequencerTabCoordinator:
    """A coordinator with only the collaborators the follow-playback handlers touch."""
    instance = object.__new__(SequencerTabCoordinator)
    instance._song_player_logic = MagicMock()
    instance._sequencer_grid_logic = MagicMock()
    instance._sequencer_grid_panel = MagicMock()
    instance._sequencer_order_panel = MagicMock()
    return instance


class TestFollowPlayback:
    def test_position_change_follows_playhead_when_enabled(
        self,
        playback_coordinator: SequencerTabCoordinator,
    ) -> None:
        playback_coordinator._song_player_logic.follow_playback = True

        playback_coordinator._on_player_position_changed(2, 5)

        playback_coordinator._sequencer_grid_panel.set_playing_row.assert_called_once_with(5)
        playback_coordinator._sequencer_order_panel.set_playing_position.assert_called_once_with(2)
        playback_coordinator._sequencer_grid_logic.select_frame.assert_called_once_with(2)

    def test_position_change_does_not_move_edited_frame_when_disabled(
        self,
        playback_coordinator: SequencerTabCoordinator,
    ) -> None:
        playback_coordinator._song_player_logic.follow_playback = False

        playback_coordinator._on_player_position_changed(2, 5)

        playback_coordinator._sequencer_grid_panel.set_playing_row.assert_called_once_with(5)
        playback_coordinator._sequencer_order_panel.set_playing_position.assert_called_once_with(2)
        playback_coordinator._sequencer_grid_logic.select_frame.assert_not_called()

    def test_order_selection_seeks_playhead_when_following(
        self,
        playback_coordinator: SequencerTabCoordinator,
    ) -> None:
        playback_coordinator._song_player_logic.follow_playback = True

        playback_coordinator._on_order_frame_selected(3)

        playback_coordinator._sequencer_grid_logic.select_frame.assert_called_once_with(3)
        playback_coordinator._song_player_logic.seek.assert_called_once_with(3)

    def test_order_selection_only_edits_when_not_following(
        self,
        playback_coordinator: SequencerTabCoordinator,
    ) -> None:
        playback_coordinator._song_player_logic.follow_playback = False

        playback_coordinator._on_order_frame_selected(3)

        playback_coordinator._sequencer_grid_logic.select_frame.assert_called_once_with(3)
        playback_coordinator._song_player_logic.seek.assert_not_called()


class TestNoteOffDispatch:
    def test_channel_cell_writes_note_off_to_that_channel(
        self,
        playback_coordinator: SequencerTabCoordinator,
    ) -> None:
        playback_coordinator._on_set_note_off(2, GeneratorName.PULSE1)

        playback_coordinator._sequencer_grid_logic.set_note_off.assert_called_once_with(GeneratorName.PULSE1, 2)
        playback_coordinator._sequencer_grid_logic.set_note_off_all_generators.assert_not_called()

    def test_sample_column_cuts_every_channel(
        self,
        playback_coordinator: SequencerTabCoordinator,
    ) -> None:
        playback_coordinator._on_set_note_off(2, None)

        playback_coordinator._sequencer_grid_logic.set_note_off_all_generators.assert_called_once_with(2)
        playback_coordinator._sequencer_grid_logic.set_note_off.assert_not_called()


@pytest.fixture
def order_ops_coordinator() -> SequencerTabCoordinator:
    """A coordinator with only the collaborators the order-frame handlers touch."""
    instance = object.__new__(SequencerTabCoordinator)
    instance._sequencer_order_logic = MagicMock()
    instance._sequencer_grid_logic = MagicMock()
    instance._sequencer_order_panel = MagicMock()
    instance._song_player_logic = MagicMock()
    instance._project_controller = MagicMock()
    instance._playing_order = None
    return instance


class TestOrderFrameOperations:
    def test_insert_adds_a_frame_after_the_target(
        self,
        order_ops_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = order_ops_coordinator
        coordinator._song_player_logic.is_playing.return_value = False

        coordinator._on_order_insert(2)

        coordinator._sequencer_order_logic.insert_frame.assert_called_once_with(3)

    def test_remove_pulls_playhead_earlier_when_playing(
        self,
        order_ops_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = order_ops_coordinator
        coordinator._playing_order = 3
        coordinator._project_controller.order_length = 5

        coordinator._on_order_remove(1)

        coordinator._sequencer_order_logic.remove_from_order.assert_called_once_with(1)
        coordinator._song_player_logic.relocate.assert_called_once_with(2)

    def test_remove_does_not_relocate_when_not_playing(
        self,
        order_ops_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = order_ops_coordinator
        coordinator._playing_order = None
        coordinator._project_controller.order_length = 5

        coordinator._on_order_remove(1)

        coordinator._song_player_logic.relocate.assert_not_called()

    def test_duplicate_before_playhead_shifts_it_later(
        self,
        order_ops_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = order_ops_coordinator
        coordinator._playing_order = 2
        coordinator._song_player_logic.is_playing.return_value = True

        coordinator._on_order_duplicate(0)

        coordinator._sequencer_order_logic.duplicate_frame.assert_called_once_with(0)
        coordinator._song_player_logic.relocate.assert_called_once_with(3)

    def test_move_makes_the_playing_frame_follow_itself(
        self,
        order_ops_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = order_ops_coordinator
        coordinator._playing_order = 2
        coordinator._song_player_logic.is_playing.return_value = True

        coordinator._on_order_move(2, 5)

        coordinator._sequencer_order_logic.move_frame.assert_called_once_with(2, 5)
        coordinator._song_player_logic.relocate.assert_called_once_with(5)

    def test_move_advances_cursor_and_highlight_immediately(
        self,
        order_ops_coordinator: SequencerTabCoordinator,
    ) -> None:
        # The cursor and playing highlight must advance on the keypress, not on the next row
        # update, so a rapid second Alt+arrow acts on the moved frame rather than snapping back.
        coordinator = order_ops_coordinator
        coordinator._playing_order = 2
        coordinator._song_player_logic.is_playing.return_value = True

        coordinator._on_order_move(2, 3)

        coordinator._sequencer_grid_logic.select_frame.assert_called_once_with(3)
        coordinator._sequencer_order_panel.set_playing_position.assert_called_once_with(3)

    def test_clear_leaves_the_playhead_in_place(
        self,
        order_ops_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = order_ops_coordinator
        coordinator._playing_order = 2

        coordinator._on_order_clear(2)

        coordinator._sequencer_order_logic.clear_frame.assert_called_once_with(2)
        coordinator._song_player_logic.relocate.assert_not_called()

    def test_play_from_seeks_when_already_playing(
        self,
        order_ops_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = order_ops_coordinator
        coordinator._song_player_logic.is_playing.return_value = True

        coordinator._on_order_play_from(3)

        coordinator._song_player_logic.seek.assert_called_once_with(3)
        coordinator._song_player_logic.play_from.assert_not_called()

    def test_play_from_starts_playback_when_stopped(
        self,
        order_ops_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = order_ops_coordinator
        coordinator._song_player_logic.is_playing.return_value = False

        coordinator._on_order_play_from(3)

        coordinator._song_player_logic.play_from.assert_called_once_with(3)
        coordinator._song_player_logic.seek.assert_not_called()


class TestImportReconstruction:
    def test_closed_project_shows_dialog_and_does_not_import(
        self,
        coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator._project_controller.is_open = False

        coordinator.import_reconstruction(Path("reconstruction.stn"))

        coordinator._dialogs.show_info.assert_called_once()
        coordinator._sequencer_browser_logic.load_reconstruction.assert_not_called()
        coordinator._on_tab_switch.assert_not_called()

    def test_successful_import_switches_to_sequencer_tab(
        self,
        coordinator: SequencerTabCoordinator,
    ) -> None:
        reconstruction = coordinator._sequencer_browser_logic.load_reconstruction.return_value

        coordinator.import_reconstruction(Path("reconstruction.stn"))

        coordinator._sequencer_browser_logic.add_reconstruction.assert_called_once_with(
            reconstruction, "reconstruction"
        )
        coordinator._on_tab_switch.assert_called_once_with(Tab.SEQUENCER)
        coordinator._dialogs.show_info.assert_not_called()
        coordinator._dialogs.show_confirmation.assert_not_called()

    def test_failed_load_shows_error_and_does_not_switch_tab(
        self,
        coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator._sequencer_browser_logic.load_reconstruction.side_effect = ValueError("invalid")

        coordinator.import_reconstruction(Path("reconstruction.stn"))

        coordinator._dialogs.show_error.assert_called_once()
        coordinator._sequencer_browser_logic.add_reconstruction.assert_not_called()
        coordinator._on_tab_switch.assert_not_called()


class TestImportFrequencyCheck:
    def test_matching_frequency_adds_without_prompt_or_adopt(
        self,
        coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator._sequencer_grid_logic.settings.nes_frequency = 60
        coordinator._sequencer_browser_logic.load_reconstruction.return_value.config.nes_frequency = 60

        coordinator.import_reconstruction(Path("reconstruction.stn"))

        coordinator._dialogs.show_confirmation.assert_not_called()
        coordinator._sequencer_grid_logic.set_nes_frequency.assert_not_called()
        coordinator._sequencer_browser_logic.add_reconstruction.assert_called_once()

    def test_empty_project_adopts_reconstruction_frequency_silently(
        self,
        coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator._project_controller.has_samples = False
        coordinator._sequencer_grid_logic.settings.nes_frequency = 60
        coordinator._sequencer_browser_logic.load_reconstruction.return_value.config.nes_frequency = 50

        coordinator.import_reconstruction(Path("reconstruction.stn"))

        coordinator._sequencer_grid_logic.set_nes_frequency.assert_called_once_with(50)
        coordinator._sequencer_browser_logic.add_reconstruction.assert_called_once()
        coordinator._dialogs.show_confirmation.assert_not_called()
        coordinator._on_tab_switch.assert_called_once_with(Tab.SEQUENCER)

    def test_mismatch_with_samples_confirms_before_adding(
        self,
        coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator._project_controller.has_samples = True
        coordinator._sequencer_grid_logic.settings.nes_frequency = 60
        coordinator._sequencer_browser_logic.load_reconstruction.return_value.config.nes_frequency = 50

        coordinator.import_reconstruction(Path("reconstruction.stn"))

        coordinator._dialogs.show_confirmation.assert_called_once()
        coordinator._sequencer_grid_logic.set_nes_frequency.assert_not_called()
        coordinator._sequencer_browser_logic.add_reconstruction.assert_not_called()
        coordinator._on_tab_switch.assert_not_called()

        confirmation = coordinator._dialogs.show_confirmation.call_args.kwargs
        assert confirmation["message"] == "recon 50 vs project 60"
        confirmation["on_confirm"]()

        coordinator._sequencer_browser_logic.add_reconstruction.assert_called_once()
        coordinator._on_tab_switch.assert_called_once_with(Tab.SEQUENCER)


@pytest.fixture
def history_coordinator() -> SequencerTabCoordinator:
    """A coordinator with only the history collaborator wired."""
    instance = object.__new__(SequencerTabCoordinator)
    instance._history = MagicMock()
    return instance


@pytest.fixture
def wired_history_coordinator(monkeypatch: pytest.MonkeyPatch) -> SequencerTabCoordinator:
    """A coordinator whose history wiring matches production.

    A real manager observes a real controller, and every project replacement —
    including the ones undo/redo drive — routes back through
    ``_on_project_replaced``, exactly as ``_wire_callbacks`` sets it up. The
    panel-refreshing ``refresh`` is stubbed since no GUI subtree exists here.
    """
    instance = object.__new__(SequencerTabCoordinator)
    controller = ProjectController(ProjectManager())
    history = HistoryManager(controller, budget=10, strict=True)
    controller.on_mutation = history.handle_mutation
    controller.on_project_replaced = instance._on_project_replaced
    instance._project_controller = controller
    instance._history = history
    monkeypatch.setattr(instance, "refresh", MagicMock())
    controller.new()
    return instance


class TestHistoryResetWiring:
    def test_project_replacement_reseeds_history(
        self,
        wired_history_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = wired_history_coordinator
        controller = coordinator._project_controller
        with coordinator._history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)

        controller.replace_project(snapshot_project(controller.project), clean=False)

        assert len(coordinator._history.entries) == 1
        assert coordinator._history.entries[0].action is HistoryAction.INITIAL

    def test_closing_the_project_empties_history(
        self,
        wired_history_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = wired_history_coordinator
        controller = coordinator._project_controller
        with coordinator._history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)

        controller.close()

        assert len(coordinator._history.entries) == 0
        assert coordinator._history.can_undo is False

    def test_undo_keeps_the_stack_it_navigates(
        self,
        wired_history_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = wired_history_coordinator
        controller = coordinator._project_controller
        with coordinator._history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)
        with coordinator._history.transaction(HistoryAction.SET_SPEED):
            controller.set_speed(4)

        coordinator.undo()

        assert len(coordinator._history.entries) == 3
        assert coordinator._history.can_redo is True
        assert controller.project.settings.tempo == 150


class TestHistoryDelegation:
    def test_undo_delegates_to_history(self, history_coordinator: SequencerTabCoordinator) -> None:
        history_coordinator.undo()

        history_coordinator._history.undo.assert_called_once_with()

    def test_redo_delegates_to_history(self, history_coordinator: SequencerTabCoordinator) -> None:
        history_coordinator.redo()

        history_coordinator._history.redo.assert_called_once_with()

    def test_jump_delegates_to_history(self, history_coordinator: SequencerTabCoordinator) -> None:
        history_coordinator.jump_to_history(3)

        history_coordinator._history.jump_to.assert_called_once_with(3)


class TestUndoableWrapper:
    def test_wrapped_call_runs_inside_a_transaction(self, history_coordinator: SequencerTabCoordinator) -> None:
        target = MagicMock()

        wrapped = history_coordinator._undoable(HistoryAction.SET_TEMPO, target)
        wrapped(150)

        history_coordinator._history.transaction.assert_called_once_with(
            HistoryAction.SET_TEMPO,
            detail=(),
            coalesce=None,
        )
        target.assert_called_once_with(150)

    def test_wrapped_call_passes_computed_detail(self, history_coordinator: SequencerTabCoordinator) -> None:
        target = MagicMock()
        segments = (HistoryDetailSegment(text="v150", role=HistoryDetailRole.VALUE),)

        wrapped = history_coordinator._undoable(HistoryAction.SET_TEMPO, target, detail=lambda _: segments)
        wrapped(150)

        history_coordinator._history.transaction.assert_called_once_with(
            HistoryAction.SET_TEMPO,
            detail=segments,
            coalesce=None,
        )

    def test_wrapped_call_passes_computed_coalesce_key(self, history_coordinator: SequencerTabCoordinator) -> None:
        target = MagicMock()

        wrapped = history_coordinator._undoable(
            HistoryAction.SET_TEMPO,
            target,
            coalesce=lambda _: ("tempo",),
        )
        wrapped(150)

        history_coordinator._history.transaction.assert_called_once_with(
            HistoryAction.SET_TEMPO,
            detail=(),
            coalesce=("tempo",),
        )
