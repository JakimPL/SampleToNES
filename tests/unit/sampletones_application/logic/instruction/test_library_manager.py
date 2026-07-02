from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.updates import LibrarySettingsUpdate
from sampletones_application.logic.instruction.library_manager import (
    InstructionsLibraryManager,
)
from sampletones_core.library import InstructionLibraryKey


@pytest.fixture
def config_manager(tmp_path: Path) -> ConfigManager:
    return ConfigManager(tmp_path / "config.json", dialogs=MagicMock())


@pytest.fixture
def library_manager(
    config_manager: ConfigManager,
    tmp_path: Path,
) -> InstructionsLibraryManager:
    manager = InstructionsLibraryManager(config_manager, language_manager=MagicMock())
    manager.set_library_directory(tmp_path / "libraries")
    return manager


def _set_transformation_gamma(config_manager: ConfigManager, gamma: int) -> None:
    library = config_manager.config.library
    config_manager.apply_library_settings(
        LibrarySettingsUpdate(
            sample_rate=library.sample_rate,
            nes_frequency=library.nes_frequency,
            spectrum_method=library.spectrum_method,
            transformation_gamma=gamma,
        )
    )


def _create_library_file(
    library_manager: InstructionsLibraryManager,
    key: InstructionLibraryKey,
) -> None:
    path = library_manager.get_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


class TestConversionLibraryReadiness:
    """Guards the contract the conversion flow relies on.

    Conversion reconstructs from the library identified by the *current* configuration, so
    library readiness must be judged by the configuration's key, never by the key of whatever
    library happens to be loaded. Conflating the two caused the loaded library's parameters to
    be reapplied over the user's freshly changed settings (see the convert/reconstruct flow).
    """

    def test_availability_tracks_current_config_not_loaded_key(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        _set_transformation_gamma(config_manager, 50)
        previous_key = config_manager.key
        _create_library_file(library_manager, previous_key)
        library_manager.sync_with_config_key(previous_key)

        _set_transformation_gamma(config_manager, 100)

        assert library_manager.is_library_available_for_config() is False
        assert library_manager.does_library_exist() is True
        assert config_manager.config.library.transformation_gamma == 100

    def test_availability_true_when_current_config_library_exists(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        _set_transformation_gamma(config_manager, 100)
        _create_library_file(library_manager, config_manager.key)

        assert library_manager.is_library_available_for_config() is True
