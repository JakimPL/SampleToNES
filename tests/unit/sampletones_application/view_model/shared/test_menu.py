from dataclasses import dataclass

import pytest

from sampletones_application.view_model.sequencer.channels import (
    SequencerChannelsViewModel,
)
from sampletones_application.view_model.shared.menu import MenuBarViewModel

EVERY_CHANNEL_AUDIBLE = SequencerChannelsViewModel(muted=frozenset())


@dataclass(frozen=True, kw_only=True)
class EnablementCase:
    label: str
    project_open: bool
    can_undo: bool
    can_redo: bool
    undo_enabled: bool
    redo_enabled: bool


ENABLEMENT_CASES = [
    EnablementCase(
        label="closed_project_disables_both",
        project_open=False,
        can_undo=True,
        can_redo=True,
        undo_enabled=False,
        redo_enabled=False,
    ),
    EnablementCase(
        label="baseline_history_disables_both",
        project_open=True,
        can_undo=False,
        can_redo=False,
        undo_enabled=False,
        redo_enabled=False,
    ),
    EnablementCase(
        label="undoable_edit_enables_undo",
        project_open=True,
        can_undo=True,
        can_redo=False,
        undo_enabled=True,
        redo_enabled=False,
    ),
    EnablementCase(
        label="undone_edit_enables_redo",
        project_open=True,
        can_undo=False,
        can_redo=True,
        undo_enabled=False,
        redo_enabled=True,
    ),
]


class TestUndoRedoEnablement:
    @pytest.mark.parametrize("case", ENABLEMENT_CASES, ids=lambda case: case.label)
    def test_enablement_follows_project_and_history_state(self, case: EnablementCase) -> None:
        view_model = MenuBarViewModel(
            project_open=case.project_open,
            reconstruction_loaded=False,
            reconstruction_saveable=False,
            reconstruction_in_project=False,
            reconstruction_file_backed=False,
            reconstruction_audio_recorded=False,
            can_undo=case.can_undo,
            can_redo=case.can_redo,
            play_label="Play",
            play_or_pause_enabled=False,
            play_from_start_enabled=False,
            play_from_frame_enabled=False,
            pause_enabled=False,
            player_paused=False,
            stop_enabled=False,
            autoplay=False,
            follow_playback=False,
            loop_song=False,
            channels=EVERY_CHANNEL_AUDIBLE,
            fullscreen=False,
            advanced_settings=False,
        )

        assert view_model.undo_enabled is case.undo_enabled
        assert view_model.redo_enabled is case.redo_enabled


class TestSaveEnablementIndependentOfLoaded:
    @pytest.mark.parametrize("reconstruction_loaded", [True, False])
    @pytest.mark.parametrize("reconstruction_saveable", [True, False])
    def test_save_flag_is_carried_verbatim(
        self,
        reconstruction_loaded: bool,
        reconstruction_saveable: bool,
    ) -> None:
        view_model = MenuBarViewModel(
            project_open=True,
            reconstruction_loaded=reconstruction_loaded,
            reconstruction_saveable=reconstruction_saveable,
            reconstruction_in_project=False,
            reconstruction_file_backed=False,
            reconstruction_audio_recorded=False,
            can_undo=False,
            can_redo=False,
            play_label="Play",
            play_or_pause_enabled=False,
            play_from_start_enabled=False,
            play_from_frame_enabled=False,
            pause_enabled=False,
            player_paused=False,
            stop_enabled=False,
            autoplay=False,
            follow_playback=False,
            loop_song=False,
            channels=EVERY_CHANNEL_AUDIBLE,
            fullscreen=False,
            advanced_settings=False,
        )

        assert view_model.reconstruction_saveable is reconstruction_saveable
        assert view_model.reconstruction_loaded is reconstruction_loaded
