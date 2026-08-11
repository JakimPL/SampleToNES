from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, Final, List
from unittest.mock import MagicMock

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.playback import FollowMode
from sampletones_application.coordinators.playback.guard import GuardedPlayer
from sampletones_application.coordinators.tabs.sequencer import SequencerTabCoordinator
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.history.snapshot import HistoryEntry
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.channels import (
    ALL_CHANNELS,
    SequencerChannelsLogic,
)
from sampletones_application.logic.sequencer.clipboard import SequencerClipboard
from sampletones_application.logic.sequencer.tracker import (
    SequencerTrackerLogic,
    TrackerBlockReader,
)
from sampletones_application.logic.shared.project_source import snapshot_project
from sampletones_application.paths import LANG_EN
from sampletones_application.ui.panels.sequencer import channels as channels_module
from sampletones_application.ui.panels.sequencer import tracker as tracker_module
from sampletones_application.ui.panels.sequencer.order import GUISequencerOrderPanel
from sampletones_application.ui.panels.sequencer.tracker import GUISequencerTrackerPanel
from sampletones_application.utils.gui.keyboard.modifiers import CTRL, NO_MODIFIERS
from sampletones_application.view_model.sequencer.region import TrackerRegion
from sampletones_application.view_model.sequencer.samples import SampleSelection
from sampletones_application.view_model.sequencer.slot import TrackerSlot
from sampletones_application.view_model.sequencer.song_player import SongPlayerViewModel
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.shared.history import (
    HistoryDetailRole,
    HistoryDetailSegment,
    HistoryDetailWord,
    HistoryDetailWordSegment,
)
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.song_position import SongPosition
from sampletones_shared.exceptions import InvalidReconstructionValuesError
from tests.suite.language import FakeLanguageManager

FREQUENCY_MISMATCH_MESSAGE_KEY: Final[str] = "global.dialog.message.frequency_mismatch"
REMOVE_SAMPLE_MESSAGE_KEY: Final[str] = "global.dialog.message.remove_sample"

TEXTS: Final[Dict[str, str]] = {
    FREQUENCY_MISMATCH_MESSAGE_KEY: "recon {reconstruction} vs project {project}",
    REMOVE_SAMPLE_MESSAGE_KEY: "Remove {name}?",
}


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
    instance._sequencer_tracker_logic = MagicMock()
    instance._sequencer_tracker_logic.settings.nes_frequency = 60
    instance._dialogs = MagicMock()
    instance._on_tab_switch = MagicMock()
    instance._language_manager = FakeLanguageManager(TEXTS)
    instance._msg_no_project = "no project"
    instance._ttl_no_project = "No project open"
    return instance


@pytest.fixture
def samples_coordinator() -> SequencerTabCoordinator:
    """A coordinator with only the collaborators the samples-menu handlers touch."""
    instance = object.__new__(SequencerTabCoordinator)
    instance._history = MagicMock()
    instance._history_detail = MagicMock()
    instance._sequencer_samples_logic = MagicMock()
    instance._dialogs = MagicMock()
    instance._language_manager = FakeLanguageManager(TEXTS)
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
    instance._sequencer_tracker_logic = MagicMock()
    instance._sequencer_tracker_logic.settings.nes_frequency = 60
    instance._project_controller = MagicMock()
    instance._project_controller.has_samples = True
    instance._dialogs = MagicMock()
    instance._on_nes_frequency_changed = MagicMock()
    instance._nes_frequency_change_acknowledged = False
    instance._language_manager = FakeLanguageManager(TEXTS)
    return instance


class TestRequestNesFrequencyChange:
    def test_unchanged_value_does_nothing(
        self,
        nes_frequency_coordinator: SequencerTabCoordinator,
    ) -> None:
        nes_frequency_coordinator._request_nes_frequency_change(60)

        nes_frequency_coordinator._sequencer_tracker_logic.set_nes_frequency.assert_not_called()
        nes_frequency_coordinator._dialogs.show_confirmation.assert_not_called()

    def test_applies_without_confirmation_when_no_samples(
        self,
        nes_frequency_coordinator: SequencerTabCoordinator,
    ) -> None:
        nes_frequency_coordinator._project_controller.has_samples = False

        nes_frequency_coordinator._request_nes_frequency_change(30)

        nes_frequency_coordinator._sequencer_tracker_logic.set_nes_frequency.assert_called_once_with(30)
        nes_frequency_coordinator._dialogs.show_confirmation.assert_not_called()

    def test_applies_without_confirmation_once_acknowledged(
        self,
        nes_frequency_coordinator: SequencerTabCoordinator,
    ) -> None:
        nes_frequency_coordinator._nes_frequency_change_acknowledged = True

        nes_frequency_coordinator._request_nes_frequency_change(30)

        nes_frequency_coordinator._sequencer_tracker_logic.set_nes_frequency.assert_called_once_with(30)
        nes_frequency_coordinator._dialogs.show_confirmation.assert_not_called()

    def test_prompts_before_applying_when_samples_exist(
        self,
        nes_frequency_coordinator: SequencerTabCoordinator,
    ) -> None:
        nes_frequency_coordinator._request_nes_frequency_change(30)

        nes_frequency_coordinator._dialogs.show_confirmation.assert_called_once()
        nes_frequency_coordinator._sequencer_tracker_logic.set_nes_frequency.assert_not_called()

        confirmation = nes_frequency_coordinator._dialogs.show_confirmation.call_args.kwargs
        confirmation["on_confirm"]()
        nes_frequency_coordinator._sequencer_tracker_logic.set_nes_frequency.assert_called_once_with(30)

    def test_applying_requests_a_retune_of_the_samples(
        self,
        nes_frequency_coordinator: SequencerTabCoordinator,
    ) -> None:
        nes_frequency_coordinator._request_nes_frequency_change(30)

        confirmation = nes_frequency_coordinator._dialogs.show_confirmation.call_args.kwargs
        confirmation["on_confirm"]()

        nes_frequency_coordinator._on_nes_frequency_changed.assert_called_once_with(30)

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

        nes_frequency_coordinator._sequencer_tracker_logic.push_settings.assert_called_once()


SOUNDING_ROW: Final[int] = 7


def _playhead(frame_index: int, row_index: int) -> SongPosition:
    """The playhead standing on a row of an order frame."""
    return SongPosition(order_position=frame_index, row_index=row_index)


def _player_view(*, follow_mode: FollowMode) -> SongPlayerViewModel:
    """A stopped transport view, which is what the coordinator reads the follow behaviour from."""
    return SongPlayerViewModel(
        is_loaded=True,
        is_playing=False,
        is_paused=False,
        follow_mode=follow_mode,
        order_position=0,
        row_index=0,
        error=None,
    )


@pytest.fixture
def playback_coordinator() -> SequencerTabCoordinator:
    """A coordinator with only the collaborators the follow-playback handlers touch."""
    instance = object.__new__(SequencerTabCoordinator)
    instance._song_player_logic = MagicMock()
    instance._sequencer_tracker_logic = MagicMock()
    instance._sequencer_tracker_panel = MagicMock()
    instance._sequencer_order_panel = MagicMock()
    instance._playing_position = None
    return instance


class TestFollowMode:
    @pytest.mark.parametrize("mode", list(FollowMode), ids=str)
    def test_the_sounding_frame_is_shown_while_the_mode_follows_patterns(
        self,
        playback_coordinator: SequencerTabCoordinator,
        mode: FollowMode,
    ) -> None:
        """The marks move on every mode; only a following mode moves the frame that is edited."""
        playback_coordinator._song_player_logic.follow_mode = mode

        playback_coordinator._on_player_position_changed(2, 5)

        panel = playback_coordinator._sequencer_tracker_panel
        panel.set_playing_position.assert_called_once_with(_playhead(2, 5))
        playback_coordinator._sequencer_order_panel.set_playing_position.assert_called_once_with(2)
        assert playback_coordinator._sequencer_tracker_logic.select_frame.called is mode.follows_pattern

    def test_the_frame_is_selected_before_the_row_is_marked(
        self,
        playback_coordinator: SequencerTabCoordinator,
    ) -> None:
        """The mark and the scroll that reveals it land on the pattern the playhead has reached."""
        playback_coordinator._song_player_logic.follow_mode = FollowMode.ROWS
        recorder = MagicMock()
        recorder.attach_mock(playback_coordinator._sequencer_tracker_logic, "logic")
        recorder.attach_mock(playback_coordinator._sequencer_tracker_panel, "panel")

        playback_coordinator._on_player_position_changed(2, 5)

        names = [name for name, _, _ in recorder.mock_calls]
        assert names.index("logic.select_frame") < names.index("panel.set_playing_position")

    @pytest.mark.parametrize("mode", list(FollowMode), ids=str)
    def test_the_view_states_whether_the_grid_follows_the_row(
        self,
        playback_coordinator: SequencerTabCoordinator,
        mode: FollowMode,
    ) -> None:
        playback_coordinator._on_player_view_changed(_player_view(follow_mode=mode))

        panel = playback_coordinator._sequencer_tracker_panel
        panel.set_row_following.assert_called_once_with(mode.follows_row)

    def test_a_stopped_view_drops_the_marks(
        self,
        playback_coordinator: SequencerTabCoordinator,
    ) -> None:
        playback_coordinator._on_player_view_changed(_player_view(follow_mode=FollowMode.ROWS))

        playback_coordinator._sequencer_tracker_panel.set_playing_position.assert_called_once_with(None)
        playback_coordinator._sequencer_order_panel.set_playing_position.assert_called_once_with(None)

    @pytest.mark.parametrize("mode", list(FollowMode), ids=str)
    def test_order_selection_seeks_the_playhead_while_following(
        self,
        playback_coordinator: SequencerTabCoordinator,
        mode: FollowMode,
    ) -> None:
        """Choosing a frame always picks what is edited, and moves the playhead when following."""
        playback_coordinator._song_player_logic.follow_mode = mode

        playback_coordinator._on_order_frame_selected(3)

        playback_coordinator._sequencer_tracker_logic.select_frame.assert_called_once_with(3)
        assert playback_coordinator._song_player_logic.seek.called is mode.follows_pattern

    @pytest.mark.parametrize("mode", list(FollowMode), ids=str)
    def test_a_chosen_mode_reaches_the_player(
        self,
        playback_coordinator: SequencerTabCoordinator,
        mode: FollowMode,
    ) -> None:
        playback_coordinator.set_follow_mode(mode)

        playback_coordinator._song_player_logic.set_follow_mode.assert_called_once_with(mode)


@pytest.fixture
def order_ops_coordinator() -> SequencerTabCoordinator:
    """A coordinator with only the collaborators the order-frame handlers touch."""
    instance = object.__new__(SequencerTabCoordinator)
    instance._sequencer_order_logic = MagicMock()
    instance._sequencer_tracker_logic = MagicMock()
    instance._sequencer_order_panel = MagicMock()
    instance._sequencer_tracker_panel = MagicMock()
    instance._song_player_logic = MagicMock()
    instance._project_controller = MagicMock()
    instance._playing_position = None
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
        coordinator._playing_position = _playhead(3, SOUNDING_ROW)
        coordinator._project_controller.order_length = 5

        coordinator._on_order_remove(1)

        coordinator._sequencer_order_logic.remove_from_order.assert_called_once_with(1)
        coordinator._song_player_logic.relocate.assert_called_once_with(2)

    def test_remove_does_not_relocate_when_not_playing(
        self,
        order_ops_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = order_ops_coordinator
        coordinator._playing_position = None
        coordinator._project_controller.order_length = 5

        coordinator._on_order_remove(1)

        coordinator._song_player_logic.relocate.assert_not_called()

    def test_duplicate_before_playhead_shifts_it_later(
        self,
        order_ops_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = order_ops_coordinator
        coordinator._playing_position = _playhead(2, SOUNDING_ROW)
        coordinator._song_player_logic.is_playing.return_value = True

        coordinator._on_order_duplicate(0)

        coordinator._sequencer_order_logic.duplicate_frame.assert_called_once_with(0)
        coordinator._song_player_logic.relocate.assert_called_once_with(3)

    def test_move_makes_the_playing_frame_follow_itself(
        self,
        order_ops_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = order_ops_coordinator
        coordinator._playing_position = _playhead(2, SOUNDING_ROW)
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
        coordinator._playing_position = _playhead(2, SOUNDING_ROW)
        coordinator._song_player_logic.is_playing.return_value = True

        coordinator._on_order_move(2, 3)

        coordinator._sequencer_tracker_logic.select_frame.assert_called_once_with(3)
        coordinator._sequencer_order_panel.set_playing_position.assert_called_once_with(3)

    def test_move_carries_the_sounding_row_to_the_frame_it_lands_on(
        self,
        order_ops_coordinator: SequencerTabCoordinator,
    ) -> None:
        """The tracker's mark belongs to a frame, so an edit that moves the frame moves the mark."""
        coordinator = order_ops_coordinator
        coordinator._playing_position = _playhead(2, SOUNDING_ROW)
        coordinator._song_player_logic.is_playing.return_value = True

        coordinator._on_order_move(2, 5)

        panel = coordinator._sequencer_tracker_panel
        panel.set_playing_position.assert_called_once_with(_playhead(5, SOUNDING_ROW))

    def test_clear_leaves_the_playhead_in_place(
        self,
        order_ops_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = order_ops_coordinator
        coordinator._playing_position = _playhead(2, SOUNDING_ROW)

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
        coordinator._sequencer_browser_logic.load_reconstruction.side_effect = InvalidReconstructionValuesError(
            "invalid",
            ValueError("inner"),
        )

        coordinator.import_reconstruction(Path("reconstruction.stn"))

        coordinator._dialogs.show_error.assert_called_once()
        coordinator._sequencer_browser_logic.add_reconstruction.assert_not_called()
        coordinator._on_tab_switch.assert_not_called()


class TestImportFrequencyCheck:
    def test_matching_frequency_adds_without_prompt_or_adopt(
        self,
        coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator._sequencer_tracker_logic.settings.nes_frequency = 60
        coordinator._sequencer_browser_logic.load_reconstruction.return_value.config.nes_frequency = 60

        coordinator.import_reconstruction(Path("reconstruction.stn"))

        coordinator._dialogs.show_confirmation.assert_not_called()
        coordinator._sequencer_tracker_logic.set_nes_frequency.assert_not_called()
        coordinator._sequencer_browser_logic.add_reconstruction.assert_called_once()

    def test_empty_project_adopts_reconstruction_frequency_silently(
        self,
        coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator._project_controller.has_samples = False
        coordinator._sequencer_tracker_logic.settings.nes_frequency = 60
        coordinator._sequencer_browser_logic.load_reconstruction.return_value.config.nes_frequency = 50

        coordinator.import_reconstruction(Path("reconstruction.stn"))

        coordinator._sequencer_tracker_logic.set_nes_frequency.assert_called_once_with(50)
        coordinator._sequencer_browser_logic.add_reconstruction.assert_called_once()
        coordinator._dialogs.show_confirmation.assert_not_called()
        coordinator._on_tab_switch.assert_called_once_with(Tab.SEQUENCER)

    def test_mismatch_with_samples_confirms_before_adding(
        self,
        coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator._project_controller.has_samples = True
        coordinator._sequencer_tracker_logic.settings.nes_frequency = 60
        coordinator._sequencer_browser_logic.load_reconstruction.return_value.config.nes_frequency = 50

        coordinator.import_reconstruction(Path("reconstruction.stn"))

        coordinator._dialogs.show_confirmation.assert_called_once()
        coordinator._sequencer_tracker_logic.set_nes_frequency.assert_not_called()
        coordinator._sequencer_browser_logic.add_reconstruction.assert_not_called()
        coordinator._on_tab_switch.assert_not_called()

        confirmation = coordinator._dialogs.show_confirmation.call_args.kwargs
        assert confirmation["message"] == "recon 50 vs project 60"
        confirmation["on_confirm"]()

        coordinator._sequencer_browser_logic.add_reconstruction.assert_called_once()
        coordinator._on_tab_switch.assert_called_once_with(Tab.SEQUENCER)


@pytest.fixture
def replace_coordinator() -> SequencerTabCoordinator:
    """A coordinator with only the collaborators the browser replacement touches.

    Defaults to a two-sample project holding ``1A: bass`` selected, against a reconstruction at the
    project's frequency (60 Hz); individual tests override. ``_on_tab_switch`` stays absent, so a
    replacement reaching for it would fail the test — the browser already lives in this tab.
    """
    instance = object.__new__(SequencerTabCoordinator)
    instance._history = MagicMock()
    instance._history_detail = MagicMock()
    instance._project_controller = MagicMock()
    instance._project_controller.sample_count = 2
    instance._sequencer_browser_logic = MagicMock()
    instance._sequencer_browser_logic.load_reconstruction.return_value.config.nes_frequency = 60
    instance._sequencer_tracker_logic = MagicMock()
    instance._sequencer_tracker_logic.settings.nes_frequency = 60
    instance._sequencer_samples_logic = MagicMock()
    instance._sequencer_samples_panel = MagicMock()
    instance._sequencer_samples_panel.selection = SampleSelection(
        sample_id="bass-id",
        position=26,
        name="bass",
    )
    instance._dialogs = MagicMock()
    instance._on_sample_reconstruction_replaced = MagicMock()
    instance._language_manager = FakeLanguageManager(TEXTS)
    return instance


class TestReplaceReconstruction:
    def test_absent_selection_replaces_nothing(
        self,
        replace_coordinator: SequencerTabCoordinator,
    ) -> None:
        replace_coordinator._sequencer_samples_panel.selection = None

        replace_coordinator.replace_reconstruction(Path("kick_02.stn"))

        replace_coordinator._sequencer_browser_logic.load_reconstruction.assert_not_called()
        replace_coordinator._sequencer_browser_logic.replace_reconstruction.assert_not_called()

    def test_failed_load_shows_error_and_replaces_nothing(
        self,
        replace_coordinator: SequencerTabCoordinator,
    ) -> None:
        replace_coordinator._sequencer_browser_logic.load_reconstruction.side_effect = InvalidReconstructionValuesError(
            "invalid",
            ValueError("inner"),
        )

        replace_coordinator.replace_reconstruction(Path("kick_02.stn"))

        replace_coordinator._dialogs.show_error.assert_called_once()
        replace_coordinator._sequencer_browser_logic.replace_reconstruction.assert_not_called()
        replace_coordinator._sequencer_samples_logic.rename_sample.assert_not_called()
        replace_coordinator._on_sample_reconstruction_replaced.assert_not_called()

    def test_selected_sample_is_renamed_and_substituted(
        self,
        replace_coordinator: SequencerTabCoordinator,
    ) -> None:
        reconstruction = replace_coordinator._sequencer_browser_logic.load_reconstruction.return_value

        replace_coordinator.replace_reconstruction(Path("/reconstructions/kick_02.stn"))

        replace_coordinator._sequencer_samples_logic.rename_sample.assert_called_once_with(
            "bass-id",
            "kick_02",
        )
        replace_coordinator._sequencer_browser_logic.replace_reconstruction.assert_called_once_with(
            "bass-id",
            reconstruction,
        )
        replace_coordinator._dialogs.show_confirmation.assert_not_called()
        replace_coordinator._sequencer_tracker_logic.set_nes_frequency.assert_not_called()

    def test_rename_and_substitution_share_one_history_entry(
        self,
        replace_coordinator: SequencerTabCoordinator,
    ) -> None:
        replace_coordinator.replace_reconstruction(Path("kick_02.stn"))

        replace_coordinator._history.transaction.assert_called_once_with(
            HistoryAction.REPLACE_SAMPLE,
            detail=replace_coordinator._history_detail.replace_sample.return_value,
        )

    def test_detail_reads_the_sample_before_it_is_substituted(
        self,
        replace_coordinator: SequencerTabCoordinator,
    ) -> None:
        """The detail names the outgoing reconstruction, which the sample only holds until the swap."""
        order = MagicMock()
        order.attach_mock(replace_coordinator._history_detail.replace_sample, "detail")
        order.attach_mock(
            replace_coordinator._sequencer_browser_logic.replace_reconstruction,
            "replace",
        )

        replace_coordinator.replace_reconstruction(Path("kick_02.stn"))

        assert [call[0] for call in order.mock_calls] == ["detail", "replace"]
        replace_coordinator._history_detail.replace_sample.assert_called_once_with("bass-id", "kick_02")

    def test_replacement_is_announced_before_the_substitution(
        self,
        replace_coordinator: SequencerTabCoordinator,
    ) -> None:
        """An editor holding the sample open identifies it by the reconstruction the swap replaces."""
        reconstruction = replace_coordinator._sequencer_browser_logic.load_reconstruction.return_value
        order = MagicMock()
        order.attach_mock(replace_coordinator._on_sample_reconstruction_replaced, "announce")
        order.attach_mock(
            replace_coordinator._sequencer_browser_logic.replace_reconstruction,
            "replace",
        )

        replace_coordinator.replace_reconstruction(Path("kick_02.stn"))

        assert [call[0] for call in order.mock_calls] == ["announce", "replace"]
        replace_coordinator._on_sample_reconstruction_replaced.assert_called_once_with(
            "bass-id",
            reconstruction,
        )

    def test_sole_sample_adopts_the_reconstruction_frequency_silently(
        self,
        replace_coordinator: SequencerTabCoordinator,
    ) -> None:
        replace_coordinator._project_controller.sample_count = 1
        replace_coordinator._sequencer_browser_logic.load_reconstruction.return_value.config.nes_frequency = 50

        replace_coordinator.replace_reconstruction(Path("kick_02.stn"))

        replace_coordinator._sequencer_tracker_logic.set_nes_frequency.assert_called_once_with(50)
        replace_coordinator._sequencer_browser_logic.replace_reconstruction.assert_called_once()
        replace_coordinator._dialogs.show_confirmation.assert_not_called()

    def test_mismatch_beside_other_samples_confirms_before_replacing(
        self,
        replace_coordinator: SequencerTabCoordinator,
    ) -> None:
        replace_coordinator._sequencer_browser_logic.load_reconstruction.return_value.config.nes_frequency = 50

        replace_coordinator.replace_reconstruction(Path("kick_02.stn"))

        replace_coordinator._dialogs.show_confirmation.assert_called_once()
        replace_coordinator._sequencer_browser_logic.replace_reconstruction.assert_not_called()
        replace_coordinator._on_sample_reconstruction_replaced.assert_not_called()

        confirmation = replace_coordinator._dialogs.show_confirmation.call_args.kwargs
        assert confirmation["message"] == "recon 50 vs project 60"
        confirmation["on_confirm"]()

        replace_coordinator._sequencer_browser_logic.replace_reconstruction.assert_called_once()
        replace_coordinator._sequencer_tracker_logic.set_nes_frequency.assert_not_called()


class TestReplaceTargetLabel:
    def test_label_names_the_selected_sample(
        self,
        replace_coordinator: SequencerTabCoordinator,
    ) -> None:
        assert replace_coordinator._replace_target_label() == "1A: bass"

    def test_label_is_absent_without_a_selection(
        self,
        replace_coordinator: SequencerTabCoordinator,
    ) -> None:
        replace_coordinator._sequencer_samples_panel.selection = None

        assert replace_coordinator._replace_target_label() is None


@pytest.fixture
def history_coordinator() -> SequencerTabCoordinator:
    """A coordinator with the two collaborators an undoable gesture reaches.

    The history is a mock, so a test reads the transaction a gesture opens; the
    controller is real, so a test reads the notifications the gesture's mutations
    actually produce.
    """
    instance = object.__new__(SequencerTabCoordinator)
    instance._history = MagicMock()
    instance._project_controller = ProjectController(ProjectManager())
    return instance


@pytest.fixture
def wired_history_coordinator(
    monkeypatch: pytest.MonkeyPatch,
) -> SequencerTabCoordinator:
    """A coordinator whose history wiring matches production.

    A real manager observes a real controller, and every project replacement —
    including the ones undo/redo drive — routes back through
    ``_on_project_replaced``, exactly as ``_wire_callbacks`` sets it up. The
    channels logic is real too, since the handler decides its lifetime. The
    panel-refreshing ``refresh`` is stubbed since no GUI subtree exists here.
    """
    instance = object.__new__(SequencerTabCoordinator)
    controller = ProjectController(ProjectManager())
    history = HistoryManager(controller, budget=10, strict=True)
    controller.on_mutation = history.handle_mutation
    controller.on_project_replaced = instance._on_project_replaced
    instance._project_controller = controller
    instance._history = history
    instance._sequencer_channels_logic = SequencerChannelsLogic()
    instance._sequencer_channels_logic.on_channels_changed = lambda _: None
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

        controller.replace_project(
            snapshot_project(controller.project),
            clean=False,
        )

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


class TestChannelMuteLifetime:
    """The mute set spans history navigation and starts fresh on a document transition.

    Both arrive as the controller's single ``on_project_replaced`` signal, so these pin the
    distinction ``_on_project_replaced`` draws from ``HistoryManager.is_restoring``.
    """

    def test_undo_keeps_the_mute_set(
        self,
        wired_history_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = wired_history_coordinator
        controller = coordinator._project_controller
        channels = coordinator._sequencer_channels_logic
        with coordinator._history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)
        channels.toggle(GeneratorName.TRIANGLE)

        coordinator.undo()

        assert channels.active_channels == ALL_CHANNELS - {GeneratorName.TRIANGLE}

    def test_redo_keeps_the_mute_set(
        self,
        wired_history_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = wired_history_coordinator
        controller = coordinator._project_controller
        channels = coordinator._sequencer_channels_logic
        with coordinator._history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)
        channels.toggle(GeneratorName.NOISE)
        coordinator.undo()

        coordinator.redo()

        assert channels.active_channels == ALL_CHANNELS - {GeneratorName.NOISE}

    def test_opening_a_project_restores_every_channel(
        self,
        wired_history_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = wired_history_coordinator
        channels = coordinator._sequencer_channels_logic
        channels.solo(GeneratorName.TRIANGLE)

        coordinator._project_controller.new()

        assert channels.active_channels == ALL_CHANNELS

    def test_closing_the_project_restores_every_channel(
        self,
        wired_history_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = wired_history_coordinator
        channels = coordinator._sequencer_channels_logic
        channels.toggle(GeneratorName.PULSE1)

        coordinator._project_controller.close()

        assert channels.active_channels == ALL_CHANNELS


@pytest.fixture
def channels_coordinator(monkeypatch: pytest.MonkeyPatch) -> SequencerTabCoordinator:
    """A coordinator joining the real channels logic to a real grid panel and a real order panel.

    Each panel's colour cues reach DearPyGui, which holds no context here, so the tables are
    reported absent and a panel stops once it has recorded the mute set — which is what the
    wiring is read for. The menu bar above the tab is a recorder, so a test can read whether it
    was told. Modifiers are reported as held nowhere; a test that needs Ctrl says so.
    """
    monkeypatch.setattr(tracker_module.dpg, "does_item_exist", lambda item: False)
    monkeypatch.setattr(tracker_module.dpg, "set_value", lambda item, value: None)
    monkeypatch.setattr(channels_module, "capture_modifiers", lambda: NO_MODIFIERS)

    language_manager = LanguageManager(LANG_EN)
    instance = object.__new__(SequencerTabCoordinator)
    instance._on_channels_changed = MagicMock()
    instance._sequencer_channels_logic = SequencerChannelsLogic()
    instance._sequencer_tracker_panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    instance._sequencer_tracker_panel._current_channels = None
    instance._sequencer_tracker_panel._create_channel_switch(language_manager)
    instance._sequencer_order_panel = GUISequencerOrderPanel.__new__(GUISequencerOrderPanel)
    instance._sequencer_order_panel._current_channels = None
    instance._sequencer_order_panel._create_channel_switch(language_manager)
    instance._wire_channels_callbacks()
    return instance


class TestChannelHeaderWiring:
    """A header click reaches the mute set, and the panel is told about it in the same gesture."""

    def test_header_click_silences_that_channel(
        self,
        channels_coordinator: SequencerTabCoordinator,
    ) -> None:
        panel = channels_coordinator._sequencer_tracker_panel

        panel._on_header_clicked(0, True, GeneratorName.TRIANGLE)

        assert channels_coordinator._sequencer_channels_logic.active_channels == ALL_CHANNELS - {GeneratorName.TRIANGLE}
        assert panel._is_muted(GeneratorName.TRIANGLE)

    def test_a_second_click_returns_the_channel_to_the_mix(
        self,
        channels_coordinator: SequencerTabCoordinator,
    ) -> None:
        panel = channels_coordinator._sequencer_tracker_panel

        panel._on_header_clicked(0, True, GeneratorName.TRIANGLE)
        panel._on_header_clicked(0, True, GeneratorName.TRIANGLE)

        assert channels_coordinator._sequencer_channels_logic.active_channels == ALL_CHANNELS
        assert not panel._is_muted(GeneratorName.TRIANGLE)

    def test_ctrl_header_click_solos_that_channel(
        self,
        channels_coordinator: SequencerTabCoordinator,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(channels_module, "capture_modifiers", lambda: CTRL)
        panel = channels_coordinator._sequencer_tracker_panel

        panel._on_header_clicked(0, True, GeneratorName.PULSE2)

        assert channels_coordinator._sequencer_channels_logic.active_channels == frozenset({GeneratorName.PULSE2})

    def test_sample_header_click_silences_every_channel(
        self,
        channels_coordinator: SequencerTabCoordinator,
    ) -> None:
        panel = channels_coordinator._sequencer_tracker_panel

        panel._on_header_clicked(0, True, None)

        assert channels_coordinator._sequencer_channels_logic.active_channels == frozenset()
        assert all(panel._is_muted(generator) for generator in GeneratorName.items())

    def test_sample_header_click_restores_every_channel_from_full_silence(
        self,
        channels_coordinator: SequencerTabCoordinator,
    ) -> None:
        panel = channels_coordinator._sequencer_tracker_panel

        panel._on_header_clicked(0, True, None)
        panel._on_header_clicked(0, True, None)

        assert channels_coordinator._sequencer_channels_logic.active_channels == ALL_CHANNELS
        assert not any(panel._is_muted(generator) for generator in GeneratorName.items())

    def test_the_menu_silences_every_channel_from_a_mixed_set(
        self,
        channels_coordinator: SequencerTabCoordinator,
    ) -> None:
        panel = channels_coordinator._sequencer_tracker_panel
        panel._on_header_clicked(0, True, GeneratorName.TRIANGLE)

        panel.call(panel.on_channels_muted)

        assert channels_coordinator._sequencer_channels_logic.active_channels == frozenset()
        assert all(panel._is_muted(generator) for generator in GeneratorName.items())

    def test_the_menu_restores_every_channel_from_a_mixed_set(
        self,
        channels_coordinator: SequencerTabCoordinator,
    ) -> None:
        panel = channels_coordinator._sequencer_tracker_panel
        panel._on_header_clicked(0, True, GeneratorName.TRIANGLE)

        panel.call(panel.on_channels_unmuted)

        assert channels_coordinator._sequencer_channels_logic.active_channels == ALL_CHANNELS
        assert not any(panel._is_muted(generator) for generator in GeneratorName.items())


class TestChannelRowLabelWiring:
    """The order table's row labels switch the same mute set, and both tables hear about it."""

    def test_row_label_click_silences_that_channel(
        self,
        channels_coordinator: SequencerTabCoordinator,
    ) -> None:
        order_panel = channels_coordinator._sequencer_order_panel

        order_panel._on_label_clicked(0, True, GeneratorName.NOISE)

        assert channels_coordinator._sequencer_channels_logic.active_channels == ALL_CHANNELS - {GeneratorName.NOISE}
        assert order_panel._is_muted(GeneratorName.NOISE)

    def test_ctrl_row_label_click_solos_that_channel(
        self,
        channels_coordinator: SequencerTabCoordinator,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(channels_module, "capture_modifiers", lambda: CTRL)
        order_panel = channels_coordinator._sequencer_order_panel

        order_panel._on_label_clicked(0, True, GeneratorName.PULSE1)

        assert channels_coordinator._sequencer_channels_logic.active_channels == frozenset({GeneratorName.PULSE1})

    def test_master_row_label_click_silences_every_channel(
        self,
        channels_coordinator: SequencerTabCoordinator,
    ) -> None:
        order_panel = channels_coordinator._sequencer_order_panel

        order_panel._on_label_clicked(0, True, None)

        assert channels_coordinator._sequencer_channels_logic.active_channels == frozenset()

    def test_a_tracker_click_reaches_the_order_table(
        self,
        channels_coordinator: SequencerTabCoordinator,
    ) -> None:
        tracker_panel = channels_coordinator._sequencer_tracker_panel
        order_panel = channels_coordinator._sequencer_order_panel

        tracker_panel._on_header_clicked(0, True, GeneratorName.TRIANGLE)

        assert order_panel._is_muted(GeneratorName.TRIANGLE)

    def test_an_order_click_reaches_the_tracker(
        self,
        channels_coordinator: SequencerTabCoordinator,
    ) -> None:
        tracker_panel = channels_coordinator._sequencer_tracker_panel
        order_panel = channels_coordinator._sequencer_order_panel

        order_panel._on_label_clicked(0, True, GeneratorName.PULSE2)

        assert tracker_panel._is_muted(GeneratorName.PULSE2)

    def test_the_order_menu_silences_every_channel(
        self,
        channels_coordinator: SequencerTabCoordinator,
    ) -> None:
        order_panel = channels_coordinator._sequencer_order_panel
        order_panel._on_label_clicked(0, True, GeneratorName.TRIANGLE)

        order_panel.call(order_panel.on_channels_muted)

        assert channels_coordinator._sequencer_channels_logic.active_channels == frozenset()

    def test_the_order_menu_restores_every_channel(
        self,
        channels_coordinator: SequencerTabCoordinator,
    ) -> None:
        order_panel = channels_coordinator._sequencer_order_panel
        order_panel._on_label_clicked(0, True, GeneratorName.TRIANGLE)

        order_panel.call(order_panel.on_channels_unmuted)

        assert channels_coordinator._sequencer_channels_logic.active_channels == ALL_CHANNELS


class TestChannelMenuWiring:
    """The Playback menu switches the same mute set, and every change reaches the menu bar."""

    def test_the_menu_reads_the_mute_set_back(
        self,
        channels_coordinator: SequencerTabCoordinator,
    ) -> None:
        channels_coordinator._sequencer_channels_logic.toggle(GeneratorName.NOISE)

        assert channels_coordinator.channels.muted == frozenset({GeneratorName.NOISE})

    def test_toggling_a_channel_silences_it(
        self,
        channels_coordinator: SequencerTabCoordinator,
    ) -> None:
        channels_coordinator.toggle_channel(GeneratorName.PULSE1)

        assert channels_coordinator._sequencer_channels_logic.active_channels == ALL_CHANNELS - {GeneratorName.PULSE1}

    def test_toggling_a_channel_twice_returns_it_to_the_mix(
        self,
        channels_coordinator: SequencerTabCoordinator,
    ) -> None:
        channels_coordinator.toggle_channel(GeneratorName.PULSE1)
        channels_coordinator.toggle_channel(GeneratorName.PULSE1)

        assert channels_coordinator._sequencer_channels_logic.active_channels == ALL_CHANNELS

    def test_the_menu_restores_every_channel_from_a_solo(
        self,
        channels_coordinator: SequencerTabCoordinator,
    ) -> None:
        channels_coordinator._sequencer_channels_logic.solo(GeneratorName.TRIANGLE)

        channels_coordinator.unmute_all_channels()

        assert channels_coordinator._sequencer_channels_logic.active_channels == ALL_CHANNELS

    def test_a_menu_toggle_shows_in_both_tables(
        self,
        channels_coordinator: SequencerTabCoordinator,
    ) -> None:
        channels_coordinator.toggle_channel(GeneratorName.TRIANGLE)

        assert channels_coordinator._sequencer_tracker_panel._is_muted(GeneratorName.TRIANGLE)
        assert channels_coordinator._sequencer_order_panel._is_muted(GeneratorName.TRIANGLE)

    def test_a_table_click_tells_the_menu_bar(
        self,
        channels_coordinator: SequencerTabCoordinator,
    ) -> None:
        channels_coordinator._sequencer_tracker_panel._on_header_clicked(0, True, GeneratorName.TRIANGLE)

        channels_coordinator._on_channels_changed.assert_called_once_with()


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

    def test_wrapped_call_passes_computed_detail(
        self,
        history_coordinator: SequencerTabCoordinator,
    ) -> None:
        target = MagicMock()
        segments = (HistoryDetailSegment(text="v150", role=HistoryDetailRole.VALUE),)

        wrapped = history_coordinator._undoable(
            HistoryAction.SET_TEMPO,
            target,
            detail=lambda _: segments,
        )
        wrapped(150)

        history_coordinator._history.transaction.assert_called_once_with(
            HistoryAction.SET_TEMPO,
            detail=segments,
            coalesce=None,
        )

    def test_wrapped_call_passes_computed_coalesce_key(
        self,
        history_coordinator: SequencerTabCoordinator,
    ) -> None:
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

    def test_wrapped_call_announces_one_song_change_for_the_whole_gesture(
        self,
        history_coordinator: SequencerTabCoordinator,
    ) -> None:
        controller = history_coordinator._project_controller
        announcements: List[str] = []
        controller.on_song_changed = lambda: announcements.append("song")
        initial_length = controller.order_length

        def append_frames(count: int) -> None:
            for _ in range(count):
                controller.append_frame()

        wrapped = history_coordinator._undoable(HistoryAction.EDIT_ROW, append_frames)
        wrapped(3)

        assert controller.order_length == initial_length + 3
        assert announcements == ["song"]


@pytest.fixture
def view_coordinator() -> SequencerTabCoordinator:
    """A coordinator with only the collaborators the history view build touches."""
    instance = object.__new__(SequencerTabCoordinator)
    instance._history = MagicMock()
    instance._language_manager = LanguageManager(LANG_EN)
    return instance


def _loop_entry(loop: bool) -> HistoryEntry:
    word = HistoryDetailWord.LOOP_ON if loop else HistoryDetailWord.LOOP_OFF
    return HistoryEntry(
        project=MagicMock(),
        action=HistoryAction.SET_SAMPLE_LOOP,
        created=datetime.now(tz=UTC),
        detail=(
            HistoryDetailSegment(text="00:", role=HistoryDetailRole.SAMPLE),
            HistoryDetailWordSegment(word=word, role=HistoryDetailRole.VALUE),
        ),
    )


class TestHistoryViewModelBuild:
    def test_word_segments_resolve_to_language_text(
        self,
        view_coordinator: SequencerTabCoordinator,
    ) -> None:
        view_coordinator._history.cursor = 1
        view_coordinator._history.entries = (_loop_entry(True), _loop_entry(False))

        view_model = view_coordinator._build_history_view_model()

        assert view_model.entries[0].detail_segments == (
            HistoryDetailSegment(text="00:", role=HistoryDetailRole.SAMPLE),
            HistoryDetailSegment(text="on", role=HistoryDetailRole.VALUE),
        )
        assert view_model.entries[1].detail_segments == (
            HistoryDetailSegment(text="00:", role=HistoryDetailRole.SAMPLE),
            HistoryDetailSegment(text="off", role=HistoryDetailRole.VALUE),
        )


@pytest.fixture
def exposure_coordinator() -> SequencerTabCoordinator:
    """A coordinator with only the playback collaborators the ``player`` property touches."""
    instance = object.__new__(SequencerTabCoordinator)
    instance._song_player_logic = MagicMock()
    instance._guarded_player = GuardedPlayer(
        instance._song_player_logic,
        dialogs=MagicMock(),
        error_message="playback failed",
    )
    return instance


class TestPlayerExposure:
    def test_player_returns_the_guarded_wrapper(
        self,
        exposure_coordinator: SequencerTabCoordinator,
    ) -> None:
        assert isinstance(exposure_coordinator.player, GuardedPlayer)


PULSE1_CELL: Final[TrackerRegion] = TrackerRegion(
    first_row=0,
    last_row=0,
    first_slot=TrackerSlot(GeneratorName.PULSE1, SubColumn.INSTRUMENT).flat_index,
    last_slot=TrackerSlot(GeneratorName.PULSE1, SubColumn.VOLUME).flat_index,
)


@pytest.fixture
def block_coordinator() -> SequencerTabCoordinator:
    """A coordinator whose copy path is real, from the tracker logic through to the clipboard.

    A real manager observes the same controller production wires it to, so a test reads the
    entries a gesture actually records.
    """
    instance = object.__new__(SequencerTabCoordinator)
    controller = ProjectController(ProjectManager())
    history = HistoryManager(controller, budget=10, strict=True)
    controller.on_mutation = history.handle_mutation
    instance._project_controller = controller
    instance._history = history
    instance._sequencer_tracker_logic = SequencerTrackerLogic(controller)
    instance._clipboard = SequencerClipboard()
    instance._tracker_block_reader = TrackerBlockReader(instance._sequencer_tracker_logic)
    return instance


class TestBlockCopy:
    def test_a_copy_fills_the_clipboard_with_the_block_it_covers(
        self,
        block_coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator = block_coordinator
        with coordinator._history.transaction(HistoryAction.EDIT_ROW):
            coordinator._sequencer_tracker_logic.set_cell_subcolumn(
                0,
                GeneratorName.PULSE1,
                transpose=5,
            )

        coordinator._on_tracker_copy_block(PULSE1_CELL)

        block = coordinator._clipboard.tracker_block
        assert block is not None
        assert block.transposes[(0, 1)] == 5

    def test_a_copy_leaves_the_history_stack_as_it_stands(
        self,
        block_coordinator: SequencerTabCoordinator,
    ) -> None:
        """A gesture that only reads the project records nothing, where the edit beside it does."""
        coordinator = block_coordinator
        edit = coordinator._undoable(
            HistoryAction.EDIT_ROW,
            coordinator._sequencer_tracker_logic.write_cell,
        )
        edit(0, GeneratorName.PULSE1, None, 5, None)
        recorded = len(coordinator._history.entries)

        coordinator._on_tracker_copy_block(PULSE1_CELL)

        assert recorded > 0
        assert len(coordinator._history.entries) == recorded
