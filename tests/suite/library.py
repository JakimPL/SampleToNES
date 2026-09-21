from pathlib import Path
from typing import Final

from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.view_model.main.updates import AdvancedSettingsUpdate
from sampletones_core.configs import Config
from sampletones_core.library import InstructionLibraryData

OTHER_LIBRARIES: Final[str] = "other_libraries"


class WrittenLibrary:
    """Library data standing in for a generated library, written as an empty library this build
    reads, which is the file the catalog lists."""

    def save(self, path: Path) -> None:
        write_empty_library(path)


def write_empty_library(path: Path) -> None:
    """Writes a library holding no entries at ``path``, stated at the version this build reads."""
    path.parent.mkdir(parents=True, exist_ok=True)
    InstructionLibraryData.create(Config(), {}).save(path)


def aim_library_directory(config_manager: ConfigManager, directory: Path) -> None:
    """Points the configuration's library directory at ``directory``, as the advanced settings do."""
    config_manager.apply_advanced_settings(
        AdvancedSettingsUpdate(
            max_workers=config_manager.config.general.max_workers,
            spectrum_method=config_manager.config.library.spectrum_method,
            transformation_gamma=config_manager.config.library.transformation_gamma,
            library_directory=directory,
            reconstructions_directory=config_manager.get_reconstructions_directory(),
        )
    )
