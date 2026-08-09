from pathlib import Path
from typing import Type
from unittest.mock import patch

import pytest
import yaml

from sampletones_application.config.managers.application import ApplicationConfigManager
from sampletones_application.config.session.application.config import ApplicationConfig


class TestApplicationConfigManagerRecovery:
    def test_incompatible_master_gain_preserves_favorites(self, tmp_path: Path) -> None:
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump({"audio": {"master_gain": 5.0}, "favorites": {"paths": ["/x/y"]}}))
        with patch(
            "sampletones_application.config.managers.application.APPLICATION_CONFIG_PATH",
            path,
        ):
            manager = ApplicationConfigManager()

        assert manager.config.audio.master_gain == ApplicationConfig().audio.master_gain
        assert Path("/x/y") in manager.favorites

    def test_invalid_history_budget_recovers_to_default(self, tmp_path: Path) -> None:
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump({"history": {"budget": 0}, "favorites": {"paths": ["/x/y"]}}))
        with patch(
            "sampletones_application.config.managers.application.APPLICATION_CONFIG_PATH",
            path,
        ):
            manager = ApplicationConfigManager()

        assert manager.config.history.budget == ApplicationConfig().history.budget
        assert Path("/x/y") in manager.favorites


class TestApplicationConfigManagerPlayback:
    def _manager(self, tmp_path: Path) -> ApplicationConfigManager:
        path = tmp_path / "config.yaml"
        with patch(
            "sampletones_application.config.managers.application.APPLICATION_CONFIG_PATH",
            path,
        ):
            return ApplicationConfigManager()

    def test_toggle_autoplay_changes_value(self, tmp_path: Path) -> None:
        manager = self._manager(tmp_path)
        initial = manager.autoplay
        result = manager.toggle_autoplay()
        assert result == (not initial)
        assert manager.autoplay == (not initial)

    def test_set_follow_playback_round_trips(self, tmp_path: Path) -> None:
        manager = self._manager(tmp_path)
        manager.set_follow_playback(False)
        assert manager.follow_playback is False
        manager.set_follow_playback(True)
        assert manager.follow_playback is True

    def test_set_loop_song_round_trips(self, tmp_path: Path) -> None:
        manager = self._manager(tmp_path)
        manager.set_loop_song(True)
        assert manager.loop_song is True
        manager.set_loop_song(False)
        assert manager.loop_song is False

    def test_set_master_gain_round_trips(self, tmp_path: Path) -> None:
        manager = self._manager(tmp_path)
        manager.set_master_gain(1.5)
        assert manager.master_gain == 1.5
        manager.set_master_gain(0.0)
        assert manager.master_gain == 0.0


class TestApplicationConfigManagerShortcuts:
    def _manager(self, tmp_path: Path) -> ApplicationConfigManager:
        path = tmp_path / "config.yaml"
        with patch(
            "sampletones_application.config.managers.application.APPLICATION_CONFIG_PATH",
            path,
        ):
            return ApplicationConfigManager()

    def test_a_fresh_configuration_names_the_shipped_scheme(self, tmp_path: Path) -> None:
        manager = self._manager(tmp_path)

        assert manager.shortcut_scheme_name == ApplicationConfig().shortcuts.scheme
        assert manager.shortcut_overrides == {}

    def test_set_shortcut_scheme_name_round_trips(self, tmp_path: Path) -> None:
        manager = self._manager(tmp_path)
        manager.set_shortcut_scheme_name("compact")

        assert manager.shortcut_scheme_name == "compact"

    def test_set_shortcut_overrides_round_trips(self, tmp_path: Path) -> None:
        manager = self._manager(tmp_path)
        manager.set_shortcut_overrides({"Undo": "Ctrl+Alt+U"})

        assert manager.shortcut_overrides == {"Undo": "Ctrl+Alt+U"}

    def test_the_preferences_reach_the_file_the_session_is_saved_to(self, tmp_path: Path) -> None:
        """A rebind is read back on the next run, which is what makes it a preference."""
        path = tmp_path / "config.yaml"
        with patch(
            "sampletones_application.config.managers.application.APPLICATION_CONFIG_PATH",
            path,
        ):
            manager = ApplicationConfigManager()
            manager.set_shortcut_scheme_name("compact")
            manager.set_shortcut_overrides({"Undo": "Ctrl+Alt+U"})
            manager.save()
            reloaded = ApplicationConfigManager()

        assert reloaded.shortcut_scheme_name == "compact"
        assert reloaded.shortcut_overrides == {"Undo": "Ctrl+Alt+U"}


class TestApplicationConfigManagerSave:
    @pytest.mark.parametrize("exception_type", [PermissionError, IsADirectoryError, OSError])
    def test_save_recovers_from_file_error(self, tmp_path: Path, exception_type: Type[OSError]) -> None:
        """Config persistence degrades to logging when the disk rejects the write."""
        config_path = tmp_path / "config.yaml"
        with patch(
            "sampletones_application.config.managers.application.APPLICATION_CONFIG_PATH",
            config_path,
        ):
            manager = ApplicationConfigManager()
            with patch(
                "sampletones_application.config.managers.application.save_yaml_atomic",
                side_effect=exception_type("save failed"),
            ):
                manager.save()

        assert not config_path.exists()

    def test_save_propagates_unexpected_error(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        with patch(
            "sampletones_application.config.managers.application.APPLICATION_CONFIG_PATH",
            config_path,
        ):
            manager = ApplicationConfigManager()
            with (
                patch(
                    "sampletones_application.config.managers.application.save_yaml_atomic",
                    side_effect=RuntimeError("unexpected"),
                ),
                pytest.raises(RuntimeError),
            ):
                manager.save()
