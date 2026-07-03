from pathlib import Path
from unittest.mock import patch

import yaml

from sampletones_application.config.managers.application import ApplicationConfigManager
from sampletones_application.config.session.application.config import ApplicationConfig


class TestApplicationConfigManagerRecovery:
    def test_incompatible_volume_preserves_favorites(self, tmp_path: Path) -> None:
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump({"audio": {"volume": 5.0}, "favorites": {"paths": ["/x/y"]}}))
        with patch(
            "sampletones_application.config.managers.application.APPLICATION_CONFIG_PATH",
            path,
        ):
            manager = ApplicationConfigManager()

        assert manager.config.audio.volume == ApplicationConfig().audio.volume
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
