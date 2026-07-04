from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.logic.instruction.library_manager import (
    InstructionsLibraryManager,
)
from sampletones_application.view_model.main.updates import LibrarySettingsUpdate
from sampletones_core.library import InstructionLibraryKey


@pytest.fixture
def config_manager(tmp_path: Path) -> ConfigManager:
    return ConfigManager(tmp_path / "config.json")


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


class TestCompleteGeneration:
    """A failed library save is an operational failure the user must see.

    The save step reports file errors through the generation-error callback (the coordinator's
    dialog) and re-raises for the caller; errors outside the save contract are bug signatures
    and propagate directly.
    """

    def test_file_error_reports_and_reraises(
        self,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        library_manager._library = MagicMock()
        library_manager._library.save_data.side_effect = PermissionError("save failed")
        error_callback = MagicMock()
        completed_callback = MagicMock()
        library_manager.on_generation_error = error_callback
        library_manager.on_generation_completed = completed_callback

        with pytest.raises(PermissionError):
            library_manager._complete_generation((MagicMock(), MagicMock()))

        error_callback.assert_called_once()
        completed_callback.assert_not_called()

    def test_unexpected_error_propagates_directly(
        self,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        library_manager._library = MagicMock()
        library_manager._library.save_data.side_effect = RuntimeError("unexpected")
        error_callback = MagicMock()
        library_manager.on_generation_error = error_callback

        with pytest.raises(RuntimeError):
            library_manager._complete_generation((MagicMock(), MagicMock()))

        error_callback.assert_not_called()

    def test_successful_save_sets_current_key_and_completes(
        self,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        library_manager._library = MagicMock()
        completed_callback = MagicMock()
        library_manager.on_generation_completed = completed_callback
        key = MagicMock()

        library_manager._complete_generation((key, MagicMock()))

        assert library_manager._current_library_key is key
        completed_callback.assert_called_once()
