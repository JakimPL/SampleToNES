from pathlib import Path
from typing import Final

from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.view_model.main.updates import AdvancedSettingsUpdate

OTHER_LIBRARIES: Final[str] = "other_libraries"


class WrittenLibrary:
    """Library data standing in for a generated library, written as the file the catalog lists."""

    def save(self, path: Path) -> None:
        path.touch()


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
