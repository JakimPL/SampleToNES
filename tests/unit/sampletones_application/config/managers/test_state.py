from pathlib import Path
from typing import Type
from unittest.mock import patch

import pytest
import yaml

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.config.managers.state import ApplicationStateManager
from sampletones_application.config.session.state.state import ApplicationState


class TestApplicationStateManagerRecovery:
    def test_incompatible_field_preserves_remaining_state(self, tmp_path: Path) -> None:
        path = tmp_path / "state.yaml"
        path.write_text(yaml.safe_dump({"viewport": {"width": "huge"}, "advanced_settings": True}))
        with patch(
            "sampletones_application.config.managers.state.APPLICATION_STATE_PATH",
            path,
        ):
            manager = ApplicationStateManager()

        assert manager.advanced_settings is True
        assert manager.window_width == ApplicationState().viewport.width


class TestApplicationStateManagerInit:
    def test_instantiation_loads_application_state(self) -> None:
        manager = ApplicationStateManager()
        assert isinstance(manager.state, ApplicationState)

    def test_state_loaded_from_nonexistent_path_is_default(self) -> None:
        nonexistent = Path("/nonexistent/path/state.yaml")
        with patch(
            "sampletones_application.config.managers.state.APPLICATION_STATE_PATH",
            nonexistent,
        ):
            manager = ApplicationStateManager()

        assert isinstance(manager.state, ApplicationState)


class TestApplicationStateManagerWindowProperties:
    def test_fullscreen_property_returns_bool(self) -> None:
        manager = ApplicationStateManager()
        assert isinstance(manager.fullscreen, bool)

    def test_window_x_returns_int(self) -> None:
        manager = ApplicationStateManager()
        assert isinstance(manager.window_x, int)

    def test_window_y_returns_int(self) -> None:
        manager = ApplicationStateManager()
        assert isinstance(manager.window_y, int)

    def test_window_width_returns_int(self) -> None:
        manager = ApplicationStateManager()
        assert isinstance(manager.window_width, int)

    def test_window_height_returns_int(self) -> None:
        manager = ApplicationStateManager()
        assert isinstance(manager.window_height, int)

    def test_set_window_state_fullscreen_updates_fullscreen(self) -> None:
        manager = ApplicationStateManager()
        manager.set_window_state(True, 0, 0, 0, 0)
        assert manager.fullscreen is True

    def test_set_window_state_non_fullscreen_updates_position(self) -> None:
        manager = ApplicationStateManager()
        manager.set_window_state(False, 100, 200, 800, 600)
        assert manager.window_x == 100
        assert manager.window_y == 200
        assert manager.window_width == 800
        assert manager.window_height == 600

    def test_set_window_state_fullscreen_does_not_update_position(self) -> None:
        manager = ApplicationStateManager()
        original_x = manager.window_x
        manager.set_window_state(True, 999, 999, 999, 999)
        assert manager.window_x == original_x


class TestApplicationStateManagerTabAndAdvanced:
    def test_set_current_tab_updates_tab(self) -> None:
        manager = ApplicationStateManager()
        manager.set_current_tab(Tab.INSTRUCTIONS)
        assert manager.load_current_tab() == Tab.INSTRUCTIONS

    def test_current_tab_property_returns_tab(self) -> None:
        manager = ApplicationStateManager()
        assert isinstance(manager.current_tab, str)

    def test_toggle_show_advanced_settings_changes_value(self) -> None:
        manager = ApplicationStateManager()
        initial = manager.advanced_settings
        result = manager.toggle_show_advanced_settings()
        assert result == (not initial)
        assert manager.advanced_settings == (not initial)


class TestApplicationStateManagerCurrentPaths:
    def test_set_current_reconstruction_updates_property(self, tmp_path: Path) -> None:
        manager = ApplicationStateManager()
        path = tmp_path / "rec.json"
        manager.set_current_reconstruction(path)
        assert manager.current_reconstruction == path

    def test_set_current_reconstruction_to_none(self) -> None:
        manager = ApplicationStateManager()
        manager.set_current_reconstruction(None)
        assert manager.current_reconstruction is None

    def test_set_current_project_updates_property(self, tmp_path: Path) -> None:
        manager = ApplicationStateManager()
        path = tmp_path / "project.stp"
        manager.set_current_project(path)
        assert manager.current_project == path


class TestApplicationStateManagerLastPaths:
    def test_set_config_path_stores_directory(self, tmp_path: Path) -> None:
        manager = ApplicationStateManager()
        file_path = tmp_path / "config.json"
        manager.set_config_path(file_path)
        result = manager.get_config_path()
        assert isinstance(result, Path)

    def test_set_library_path_stores_directory(self, tmp_path: Path) -> None:
        manager = ApplicationStateManager()
        manager.set_library_path(tmp_path / "lib.json")
        assert isinstance(manager.get_library_path(), Path)

    def test_set_instrument_path_stores_directory(self, tmp_path: Path) -> None:
        manager = ApplicationStateManager()
        manager.set_instrument_path(tmp_path / "instr.json")
        assert isinstance(manager.get_instrument_path(), Path)

    def test_set_reconstruction_path_stores_directory(
        self,
        tmp_path: Path,
    ) -> None:
        manager = ApplicationStateManager()
        manager.set_reconstruction_path(tmp_path / "rec.json")
        assert isinstance(manager.get_reconstruction_path(), Path)

    def test_set_audio_path_stores_directory(self, tmp_path: Path) -> None:
        manager = ApplicationStateManager()
        manager.set_audio_path(tmp_path / "audio.wav")
        assert isinstance(manager.get_audio_path(), Path)

    def test_set_project_path_stores_directory(self, tmp_path: Path) -> None:
        manager = ApplicationStateManager()
        manager.set_project_path(tmp_path / "project.stp")
        assert isinstance(manager.get_project_path(), Path)


class TestApplicationStateManagerSave:
    def test_save_creates_state_file(self, tmp_path: Path) -> None:
        state_path = tmp_path / "state.yaml"
        with patch(
            "sampletones_application.config.managers.state.APPLICATION_STATE_PATH",
            state_path,
        ):
            manager = ApplicationStateManager()
            manager.save()

        assert state_path.exists()

    def test_save_and_reload_preserves_advanced_settings(self, tmp_path: Path) -> None:
        state_path = tmp_path / "state.yaml"
        with patch(
            "sampletones_application.config.managers.state.APPLICATION_STATE_PATH",
            state_path,
        ):
            manager = ApplicationStateManager()
            manager.toggle_show_advanced_settings()
            manager.save()
            reloaded = ApplicationStateManager()

        assert reloaded.advanced_settings == manager.advanced_settings

    @pytest.mark.parametrize("exception_type", [PermissionError, IsADirectoryError, OSError])
    def test_save_recovers_from_file_error(self, tmp_path: Path, exception_type: Type[OSError]) -> None:
        """State persistence degrades to logging when the disk rejects the write."""
        state_path = tmp_path / "state.yaml"
        with patch(
            "sampletones_application.config.managers.state.APPLICATION_STATE_PATH",
            state_path,
        ):
            manager = ApplicationStateManager()
            with patch(
                "sampletones_application.config.managers.state.save_yaml_atomic",
                side_effect=exception_type("save failed"),
            ):
                manager.save()

        assert not state_path.exists()

    def test_save_propagates_unexpected_error(self, tmp_path: Path) -> None:
        state_path = tmp_path / "state.yaml"
        with patch(
            "sampletones_application.config.managers.state.APPLICATION_STATE_PATH",
            state_path,
        ):
            manager = ApplicationStateManager()
            with patch(
                "sampletones_application.config.managers.state.save_yaml_atomic",
                side_effect=RuntimeError("unexpected"),
            ):
                with pytest.raises(RuntimeError):
                    manager.save()
