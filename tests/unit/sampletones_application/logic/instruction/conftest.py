from pathlib import Path
from typing import Final

import pytest

from sampletones_application.config.managers.config import ConfigManager
from tests.suite.application import held_queue
from tests.suite.library import aim_library_directory

LIBRARIES: Final[str] = "libraries"

__all__ = ["held_queue"]


@pytest.fixture
def config_manager(tmp_path: Path) -> ConfigManager:
    """A configuration keeping its libraries in the case's own directory."""
    manager = ConfigManager(tmp_path / "config.json")
    aim_library_directory(manager, tmp_path / LIBRARIES)
    return manager
