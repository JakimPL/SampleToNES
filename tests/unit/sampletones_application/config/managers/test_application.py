import platform
from pathlib import Path
from typing import Type
from unittest.mock import patch

import pytest
import yaml

from sampletones_application.config.managers.application import ApplicationConfigManager
from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.constants.keybindings import (
    DEFAULT_SCHEME_NAME,
    MACOS_SCHEME_NAME,
)
from sampletones_application.constants.playback import FollowMode
from sampletones_core.data.metadata import Metadata


class TestApplicationConfigManagerRecovery:
    def test_incompatible_master_gain_preserves_favorites(self, tmp_path: Path) -> None:
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump({"audio": {"master_gain": 5.0}, "favorites": {"paths": ["/x/y"]}}))

        manager = ApplicationConfigManager(path)

        assert manager.config.audio.master_gain == ApplicationConfig().audio.master_gain
        assert Path("/x/y") in manager.favorites

    def test_invalid_history_budget_recovers_to_default(self, tmp_path: Path) -> None:
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump({"history": {"budget": 0}, "favorites": {"paths": ["/x/y"]}}))

        manager = ApplicationConfigManager(path)

        assert manager.config.history.budget == ApplicationConfig().history.budget
        assert Path("/x/y") in manager.favorites


class TestApplicationConfigManagerPlayback:
    def test_toggle_autoplay_changes_value(self, tmp_path: Path) -> None:
        manager = ApplicationConfigManager(tmp_path / "config.yaml")
        initial = manager.autoplay
        result = manager.toggle_autoplay()
        assert result == (not initial)
        assert manager.autoplay == (not initial)

    @pytest.mark.parametrize("mode", list(FollowMode), ids=str)
    def test_set_follow_mode_round_trips(self, tmp_path: Path, mode: FollowMode) -> None:
        manager = ApplicationConfigManager(tmp_path / "config.yaml")
        manager.set_follow_mode(mode)
        assert manager.follow_mode is mode

    def test_set_loop_song_round_trips(self, tmp_path: Path) -> None:
        manager = ApplicationConfigManager(tmp_path / "config.yaml")
        manager.set_loop_song(True)
        assert manager.loop_song is True
        manager.set_loop_song(False)
        assert manager.loop_song is False

    def test_set_master_gain_round_trips(self, tmp_path: Path) -> None:
        manager = ApplicationConfigManager(tmp_path / "config.yaml")
        manager.set_master_gain(1.5)
        assert manager.master_gain == 1.5
        manager.set_master_gain(0.0)
        assert manager.master_gain == 0.0


class TestApplicationConfigManagerShortcuts:
    def test_a_fresh_configuration_names_the_shipped_scheme(self, tmp_path: Path) -> None:
        manager = ApplicationConfigManager(tmp_path / "config.yaml")

        assert manager.shortcut_scheme_name == ApplicationConfig().shortcuts.scheme
        assert manager.shortcut_overrides == {}

    def test_set_shortcut_scheme_name_round_trips(self, tmp_path: Path) -> None:
        manager = ApplicationConfigManager(tmp_path / "config.yaml")
        manager.set_shortcut_scheme_name("compact")

        assert manager.shortcut_scheme_name == "compact"

    def test_set_shortcut_overrides_round_trips(self, tmp_path: Path) -> None:
        manager = ApplicationConfigManager(tmp_path / "config.yaml")
        manager.set_shortcut_overrides({"Undo": "Ctrl+Alt+U"})

        assert manager.shortcut_overrides == {"Undo": "Ctrl+Alt+U"}

    def test_the_preferences_reach_the_file_the_session_is_saved_to(self, tmp_path: Path) -> None:
        """A rebind is read back on the next run, which is what makes it a preference."""
        path = tmp_path / "config.yaml"
        manager = ApplicationConfigManager(path)
        manager.set_shortcut_scheme_name("compact")
        manager.set_shortcut_overrides({"Undo": "Ctrl+Alt+U"})
        manager.save()

        reloaded = ApplicationConfigManager(path)

        assert reloaded.shortcut_scheme_name == "compact"
        assert reloaded.shortcut_overrides == {"Undo": "Ctrl+Alt+U"}


class TestApplicationConfigManagerPlatformScheme:
    """The keyboard a Mac opens on, decided when the configuration is created."""

    def test_a_fresh_configuration_on_a_mac_names_the_mac_scheme(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(platform, "system", lambda: "Darwin")

        manager = ApplicationConfigManager(tmp_path / "config.yaml")

        assert manager.shortcut_scheme_name == MACOS_SCHEME_NAME

    def test_a_configuration_carrying_no_scheme_yet_takes_the_platform_one(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A file written before the preference existed reaches the choice a fresh one makes."""
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump({"favorites": {"paths": ["/x/y"]}}))

        manager = ApplicationConfigManager(path)

        assert manager.shortcut_scheme_name == MACOS_SCHEME_NAME
        assert Path("/x/y") in manager.favorites

    def test_a_stored_scheme_stands_on_a_mac(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A reader who chose the Control keys keeps them on a machine labelled Command."""
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump({"shortcuts": {"scheme": DEFAULT_SCHEME_NAME}}))

        assert ApplicationConfigManager(path).shortcut_scheme_name == DEFAULT_SCHEME_NAME

    def test_the_platform_decides_once_and_the_file_decides_after(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The name a fresh configuration takes from its platform reaches the file, and the file
        is what every run after reads, so the platform is asked one time."""
        path = tmp_path / "config.yaml"
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        ApplicationConfigManager(path).save()

        monkeypatch.setattr(platform, "system", lambda: "Linux")
        reloaded = ApplicationConfigManager(path)

        assert yaml.safe_load(path.read_text())["shortcuts"]["scheme"] == MACOS_SCHEME_NAME
        assert reloaded.shortcut_scheme_name == MACOS_SCHEME_NAME


class TestApplicationConfigManagerMetadata:
    """The saved file names the build that wrote it."""

    def test_a_file_written_by_an_earlier_build_is_stamped_on_save(self, tmp_path: Path) -> None:
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump({"metadata": {"version": "0.0.1"}, "favorites": {"paths": ["/x/y"]}}))
        manager = ApplicationConfigManager(path)
        assert manager.config.metadata.version == "0.0.1"

        manager.save()

        assert yaml.safe_load(path.read_text())["metadata"] == Metadata.default().model_dump()

    def test_the_settings_beside_the_metadata_stand(self, tmp_path: Path) -> None:
        """Stamping the version rewrites the metadata alone, so a preference survives the save."""
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump({"metadata": {"version": "0.0.1"}, "display": {"palette": "ink"}}))
        ApplicationConfigManager(path).save()

        reloaded = ApplicationConfigManager(path)

        assert reloaded.palette_name == "ink"
        assert reloaded.config.metadata == Metadata.default()


class TestApplicationConfigManagerSave:
    @pytest.mark.parametrize("exception_type", [PermissionError, IsADirectoryError, OSError])
    def test_save_recovers_from_file_error(self, tmp_path: Path, exception_type: Type[OSError]) -> None:
        """Config persistence degrades to logging when the disk rejects the write."""
        path = tmp_path / "config.yaml"
        manager = ApplicationConfigManager(path)
        with patch(
            "sampletones_application.config.managers.application.save_yaml_atomic",
            side_effect=exception_type("save failed"),
        ):
            manager.save()

        assert not path.exists()

    def test_save_propagates_unexpected_error(self, tmp_path: Path) -> None:
        manager = ApplicationConfigManager(tmp_path / "config.yaml")
        with (
            patch(
                "sampletones_application.config.managers.application.save_yaml_atomic",
                side_effect=RuntimeError("unexpected"),
            ),
            pytest.raises(RuntimeError),
        ):
            manager.save()
