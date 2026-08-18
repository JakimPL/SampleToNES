from pathlib import Path
from typing import Type
from unittest.mock import patch

import pytest
import yaml

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.config.managers.state import ApplicationStateManager
from sampletones_application.config.session.state.state import ApplicationState
from sampletones_application.tags.reconstructions import TAG_RECONSTRUCTIONS_BROWSER_PANEL
from sampletones_application.tags.sequencer import TAG_SEQUENCER_BROWSER_PANEL


@pytest.fixture
def manager(tmp_path: Path) -> ApplicationStateManager:
    """A manager over a state file of its own, in the state a first run finds."""
    return ApplicationStateManager(tmp_path / "state.yaml")


class TestApplicationStateManagerRecovery:
    def test_incompatible_field_preserves_remaining_state(self, tmp_path: Path) -> None:
        path = tmp_path / "state.yaml"
        path.write_text(yaml.safe_dump({"viewport": {"width": "huge"}, "advanced_settings": True}))

        manager = ApplicationStateManager(path)

        assert manager.advanced_settings is True
        assert manager.window_width == ApplicationState().viewport.width


class TestApplicationStateManagerInit:
    def test_instantiation_loads_application_state(self, tmp_path: Path) -> None:
        path = tmp_path / "state.yaml"
        path.write_text(yaml.safe_dump({"advanced_settings": True}))

        manager = ApplicationStateManager(path)

        assert isinstance(manager.state, ApplicationState)
        assert manager.advanced_settings is True

    def test_state_loaded_from_nonexistent_path_is_default(self) -> None:
        manager = ApplicationStateManager(Path("/nonexistent/path/state.yaml"))

        assert isinstance(manager.state, ApplicationState)


class TestApplicationStateManagerWindowProperties:
    def test_fullscreen_property_returns_bool(self, manager: ApplicationStateManager) -> None:
        assert isinstance(manager.fullscreen, bool)

    def test_window_x_returns_int(self, manager: ApplicationStateManager) -> None:
        assert isinstance(manager.window_x, int)

    def test_window_y_returns_int(self, manager: ApplicationStateManager) -> None:
        assert isinstance(manager.window_y, int)

    def test_window_width_returns_int(self, manager: ApplicationStateManager) -> None:
        assert isinstance(manager.window_width, int)

    def test_window_height_returns_int(self, manager: ApplicationStateManager) -> None:
        assert isinstance(manager.window_height, int)

    def test_set_window_state_fullscreen_updates_fullscreen(self, manager: ApplicationStateManager) -> None:
        manager.set_window_state(True, 0, 0, 0, 0)
        assert manager.fullscreen is True

    def test_set_window_state_non_fullscreen_updates_position(self, manager: ApplicationStateManager) -> None:
        manager.set_window_state(False, 100, 200, 800, 600)
        assert manager.window_x == 100
        assert manager.window_y == 200
        assert manager.window_width == 800
        assert manager.window_height == 600

    def test_set_window_state_fullscreen_does_not_update_position(self, manager: ApplicationStateManager) -> None:
        original_x = manager.window_x
        manager.set_window_state(True, 999, 999, 999, 999)
        assert manager.window_x == original_x


class TestApplicationStateManagerTabAndAdvanced:
    def test_set_current_tab_updates_tab(self, manager: ApplicationStateManager) -> None:
        manager.set_current_tab(Tab.INSTRUCTIONS)
        assert manager.load_current_tab() == Tab.INSTRUCTIONS

    def test_current_tab_property_returns_tab(self, manager: ApplicationStateManager) -> None:
        assert isinstance(manager.current_tab, str)

    def test_toggle_show_advanced_settings_changes_value(self, manager: ApplicationStateManager) -> None:
        initial = manager.advanced_settings
        result = manager.toggle_show_advanced_settings()
        assert result == (not initial)
        assert manager.advanced_settings == (not initial)


class TestApplicationStateManagerCardsAndFilters:
    """The per-panel state a card keeps: whether it is collapsed, and what its browser narrows to."""

    def test_a_card_no_run_has_touched_reads_expanded(self, manager: ApplicationStateManager) -> None:
        assert manager.is_card_collapsed(TAG_SEQUENCER_BROWSER_PANEL) is False

    def test_a_card_reads_the_collapse_it_was_given(self, manager: ApplicationStateManager) -> None:
        manager.set_card_collapsed(TAG_SEQUENCER_BROWSER_PANEL, True)
        assert manager.is_card_collapsed(TAG_SEQUENCER_BROWSER_PANEL) is True

    def test_a_browser_no_run_has_touched_shows_the_whole_tree(self, manager: ApplicationStateManager) -> None:
        assert manager.is_favorites_filter_active(TAG_SEQUENCER_BROWSER_PANEL) is False

    def test_a_browser_reads_the_filter_it_was_given(self, manager: ApplicationStateManager) -> None:
        manager.set_favorites_filter_active(TAG_SEQUENCER_BROWSER_PANEL, True)
        assert manager.is_favorites_filter_active(TAG_SEQUENCER_BROWSER_PANEL) is True

    def test_each_browser_keeps_the_filter_of_its_own_panel(self, manager: ApplicationStateManager) -> None:
        manager.set_favorites_filter_active(TAG_SEQUENCER_BROWSER_PANEL, True)

        assert manager.is_favorites_filter_active(TAG_RECONSTRUCTIONS_BROWSER_PANEL) is False

    def test_the_filter_and_the_collapse_of_one_panel_stand_apart(self, manager: ApplicationStateManager) -> None:
        manager.set_favorites_filter_active(TAG_SEQUENCER_BROWSER_PANEL, True)

        assert manager.is_card_collapsed(TAG_SEQUENCER_BROWSER_PANEL) is False

    def test_a_browser_no_run_has_touched_stands_open_nowhere(self, manager: ApplicationStateManager) -> None:
        assert manager.expanded_rows(TAG_SEQUENCER_BROWSER_PANEL) == set()

    def test_a_browser_reads_the_rows_it_was_given(self, manager: ApplicationStateManager) -> None:
        manager.set_expanded_rows(TAG_SEQUENCER_BROWSER_PANEL, {"row.a", "row.b"})
        assert manager.expanded_rows(TAG_SEQUENCER_BROWSER_PANEL) == {"row.a", "row.b"}

    def test_each_browser_keeps_the_rows_of_its_own_panel(self, manager: ApplicationStateManager) -> None:
        manager.set_expanded_rows(TAG_SEQUENCER_BROWSER_PANEL, {"row.a"})

        assert manager.expanded_rows(TAG_RECONSTRUCTIONS_BROWSER_PANEL) == set()

    def test_an_explorer_no_run_has_touched_stands_open_nowhere(self, manager: ApplicationStateManager) -> None:
        assert manager.expanded_directories == set()

    def test_the_explorer_reads_the_folders_it_was_given(
        self,
        manager: ApplicationStateManager,
        tmp_path: Path,
    ) -> None:
        manager.set_expanded_directories({tmp_path})
        assert manager.expanded_directories == {tmp_path}

    def test_the_rows_are_written_in_a_settled_order(self, manager: ApplicationStateManager) -> None:
        """The file reads the same twice, whichever order the browser answered its rows in."""
        manager.set_expanded_rows(TAG_SEQUENCER_BROWSER_PANEL, {"row.b", "row.a"})

        assert manager.state.expanded_rows[TAG_SEQUENCER_BROWSER_PANEL] == ["row.a", "row.b"]


class TestApplicationStateManagerCurrentPaths:
    def test_set_current_reconstruction_updates_property(
        self,
        manager: ApplicationStateManager,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "rec.json"
        manager.set_current_reconstruction(path)
        assert manager.current_reconstruction == path

    def test_set_current_reconstruction_to_none(self, manager: ApplicationStateManager) -> None:
        manager.set_current_reconstruction(None)
        assert manager.current_reconstruction is None

    def test_set_current_project_updates_property(
        self,
        manager: ApplicationStateManager,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "project.stp"
        manager.set_current_project(path)
        assert manager.current_project == path


class TestApplicationStateManagerLastPaths:
    def test_set_config_path_stores_directory(
        self,
        manager: ApplicationStateManager,
        tmp_path: Path,
    ) -> None:
        manager.set_config_path(tmp_path / "config.json")
        assert isinstance(manager.get_config_path(), Path)

    def test_set_library_path_stores_directory(
        self,
        manager: ApplicationStateManager,
        tmp_path: Path,
    ) -> None:
        manager.set_library_path(tmp_path / "lib.json")
        assert isinstance(manager.get_library_path(), Path)

    def test_set_instrument_path_stores_directory(
        self,
        manager: ApplicationStateManager,
        tmp_path: Path,
    ) -> None:
        manager.set_instrument_path(tmp_path / "instr.json")
        assert isinstance(manager.get_instrument_path(), Path)

    def test_set_reconstruction_path_stores_directory(
        self,
        manager: ApplicationStateManager,
        tmp_path: Path,
    ) -> None:
        manager.set_reconstruction_path(tmp_path / "rec.json")
        assert isinstance(manager.get_reconstruction_path(), Path)

    def test_set_audio_input_path_stores_directory(
        self,
        manager: ApplicationStateManager,
        tmp_path: Path,
    ) -> None:
        manager.set_audio_input_path(tmp_path / "clip.wav")
        assert isinstance(manager.get_audio_input_path(), Path)

    def test_audio_input_and_reconstruction_paths_are_independent(
        self,
        manager: ApplicationStateManager,
        tmp_path: Path,
    ) -> None:
        reconstruction_directory = tmp_path / "reconstructions"
        audio_directory = tmp_path / "audio"
        reconstruction_directory.mkdir()
        audio_directory.mkdir()

        manager.set_reconstruction_path(reconstruction_directory / "rec.stn")
        manager.set_audio_input_path(audio_directory / "clip.wav")

        assert manager.get_reconstruction_path() == reconstruction_directory
        assert manager.get_audio_input_path() == audio_directory

    def test_set_audio_path_stores_directory(
        self,
        manager: ApplicationStateManager,
        tmp_path: Path,
    ) -> None:
        manager.set_audio_path(tmp_path / "audio.wav")
        assert isinstance(manager.get_audio_path(), Path)

    def test_set_project_path_stores_directory(
        self,
        manager: ApplicationStateManager,
        tmp_path: Path,
    ) -> None:
        manager.set_project_path(tmp_path / "project.stp")
        assert isinstance(manager.get_project_path(), Path)


class TestApplicationStateManagerSave:
    def test_save_creates_state_file(self, tmp_path: Path) -> None:
        path = tmp_path / "state.yaml"

        ApplicationStateManager(path).save()

        assert path.exists()

    def test_save_and_reload_preserves_advanced_settings(self, tmp_path: Path) -> None:
        path = tmp_path / "state.yaml"
        manager = ApplicationStateManager(path)
        manager.toggle_show_advanced_settings()
        manager.save()

        reloaded = ApplicationStateManager(path)

        assert reloaded.advanced_settings == manager.advanced_settings

    def test_save_and_reload_preserves_each_browser_filter(self, tmp_path: Path) -> None:
        """The mode a browser was left in returns on the next launch, for that browser alone."""
        path = tmp_path / "state.yaml"
        manager = ApplicationStateManager(path)
        manager.set_favorites_filter_active(TAG_SEQUENCER_BROWSER_PANEL, True)
        manager.save()

        reloaded = ApplicationStateManager(path)

        assert reloaded.is_favorites_filter_active(TAG_SEQUENCER_BROWSER_PANEL) is True

    def test_save_and_reload_preserves_the_rows_each_browser_stands_open(self, tmp_path: Path) -> None:
        """The shape the reader unfolded returns on the next launch, for that browser alone."""
        path = tmp_path / "state.yaml"
        manager = ApplicationStateManager(path)
        manager.set_expanded_rows(TAG_SEQUENCER_BROWSER_PANEL, {"row.a", "row.b"})
        manager.save()

        reloaded = ApplicationStateManager(path)

        assert reloaded.expanded_rows(TAG_SEQUENCER_BROWSER_PANEL) == {"row.a", "row.b"}
        assert reloaded.expanded_rows(TAG_RECONSTRUCTIONS_BROWSER_PANEL) == set()

    def test_save_and_reload_preserves_the_folders_the_explorer_stands_open(self, tmp_path: Path) -> None:
        """The folders the reader walked into return on the next launch, read down to as they were."""
        path = tmp_path / "state.yaml"
        manager = ApplicationStateManager(path)
        manager.set_expanded_directories({tmp_path / "music", tmp_path / "notes"})
        manager.save()

        reloaded = ApplicationStateManager(path)

        assert reloaded.expanded_directories == {tmp_path / "music", tmp_path / "notes"}
        assert reloaded.is_favorites_filter_active(TAG_RECONSTRUCTIONS_BROWSER_PANEL) is False

    @pytest.mark.parametrize("exception_type", [PermissionError, IsADirectoryError, OSError])
    def test_save_recovers_from_file_error(self, tmp_path: Path, exception_type: Type[OSError]) -> None:
        """State persistence degrades to logging when the disk rejects the write."""
        path = tmp_path / "state.yaml"
        manager = ApplicationStateManager(path)
        with patch(
            "sampletones_application.config.managers.state.save_yaml_atomic",
            side_effect=exception_type("save failed"),
        ):
            manager.save()

        assert not path.exists()

    def test_save_propagates_unexpected_error(self, tmp_path: Path) -> None:
        manager = ApplicationStateManager(tmp_path / "state.yaml")
        with (
            patch(
                "sampletones_application.config.managers.state.save_yaml_atomic",
                side_effect=RuntimeError("unexpected"),
            ),
            pytest.raises(RuntimeError),
        ):
            manager.save()
