from pathlib import Path
from typing import Final

import pytest

from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.view_model.main.updates import AdvancedSettingsUpdate

LIBRARIES: Final[str] = "libraries"


@pytest.fixture
def config_manager(tmp_path: Path) -> ConfigManager:
    """A configuration keeping its libraries in the case's own directory."""
    manager = ConfigManager(tmp_path / "config.json")
    manager.apply_advanced_settings(
        AdvancedSettingsUpdate(
            max_workers=manager.config.general.max_workers,
            spectrum_method=manager.config.library.spectrum_method,
            transformation_gamma=manager.config.library.transformation_gamma,
            library_directory=tmp_path / LIBRARIES,
            reconstructions_directory=manager.get_reconstructions_directory(),
        )
    )
    return manager
