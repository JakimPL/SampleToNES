import shutil
from pathlib import Path
from typing import List
from unittest.mock import MagicMock

import pytest

from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.logic.instruction.library_manager import (
    InstructionsLibraryManager,
)
from sampletones_application.logic.instruction.readiness import LibraryReadiness
from sampletones_application.view_model.main.updates import AdvancedSettingsUpdate
from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.library import InstructionLibraryKey, LibraryState
from tests.suite.compatibility import LIBRARY_VERSION, archived
from tests.suite.library import OTHER_LIBRARIES, WrittenLibrary, write_empty_library


@pytest.fixture
def library_manager(config_manager: ConfigManager) -> InstructionsLibraryManager:
    return InstructionsLibraryManager(config_manager, language_manager=MagicMock())


def _set_transformation_gamma(config_manager: ConfigManager, gamma: int) -> None:
    library = config_manager.config.library
    config_manager.apply_advanced_settings(
        AdvancedSettingsUpdate(
            max_workers=config_manager.config.general.max_workers,
            spectrum_method=library.spectrum_method,
            transformation_gamma=gamma,
            library_directory=config_manager.get_library_directory(),
            reconstructions_directory=config_manager.get_reconstructions_directory(),
        )
    )


def _create_library_file(
    library_manager: InstructionsLibraryManager,
    key: InstructionLibraryKey,
) -> None:
    write_empty_library(library_manager.get_path(key))


def _create_earlier_library_file(
    library_manager: InstructionsLibraryManager,
    key: InstructionLibraryKey,
) -> None:
    path = library_manager.get_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(archived(ObjectKind.LIBRARY, LIBRARY_VERSION), path)


class TestTheLibraryAConfigurationNames:
    """A library is judged by the key it is asked about, whatever library the catalog last took up."""

    def test_the_library_of_settings_changed_since_is_missing(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        _set_transformation_gamma(config_manager, 50)
        previous_key = config_manager.key
        _create_library_file(library_manager, previous_key)
        library_manager.sync_with_config_key(previous_key)

        _set_transformation_gamma(config_manager, 100)

        assert (
            library_manager.library_state(config_manager.key),
            library_manager.library_state(previous_key),
            library_manager.current_library_key,
        ) == (LibraryState.MISSING, LibraryState.CURRENT, previous_key)

    def test_a_library_another_version_built_is_left_unsynced(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        _create_earlier_library_file(library_manager, config_manager.key)

        assert (
            library_manager.library_state(config_manager.key),
            library_manager.sync_with_config_key(config_manager.key),
        ) == (LibraryState.OUTDATED, None)


class TestTheDirectoryTheCatalogStandsAt:
    """The catalog holds the libraries it loaded for as long as it reads the same directory."""

    def test_the_directory_it_stands_at_keeps_what_it_loaded(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        library_manager._library.save_data(config_manager.key, WrittenLibrary())

        library_manager.set_library_directory(config_manager.get_library_directory())

        assert library_manager.is_library_loaded(config_manager.key) is True

    def test_another_directory_starts_with_nothing_loaded(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
        tmp_path: Path,
    ) -> None:
        library_manager._library.save_data(config_manager.key, WrittenLibrary())
        other = tmp_path / OTHER_LIBRARIES

        library_manager.set_library_directory(other)

        assert (library_manager.library_directory, library_manager._library.data) == (other, {})


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
        library = MagicMock()
        library.save_data.side_effect = PermissionError("save failed")
        error_callback = MagicMock()
        completed_callback = MagicMock()
        library_manager.on_generation_error = error_callback
        library_manager.on_generation_completed = completed_callback

        with pytest.raises(PermissionError):
            library_manager._complete_generation(library, (MagicMock(), MagicMock()))

        error_callback.assert_called_once()
        completed_callback.assert_not_called()

    def test_unexpected_error_propagates_directly(
        self,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        library = MagicMock()
        library.save_data.side_effect = RuntimeError("unexpected")
        error_callback = MagicMock()
        library_manager.on_generation_error = error_callback

        with pytest.raises(RuntimeError):
            library_manager._complete_generation(library, (MagicMock(), MagicMock()))

        error_callback.assert_not_called()

    def test_successful_save_sets_current_key_and_completes(
        self,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        library_manager._library = MagicMock()
        completed_callback = MagicMock()
        library_manager.on_generation_completed = completed_callback
        key = MagicMock()

        library_manager._complete_generation(library_manager._library, (key, MagicMock()))

        assert library_manager._current_library_key is key
        completed_callback.assert_called_once()

    def test_a_library_lands_where_its_generation_started(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
        tmp_path: Path,
    ) -> None:
        started_in = library_manager._library
        library_manager.set_library_directory(tmp_path / OTHER_LIBRARIES)

        library_manager._complete_generation(started_in, (config_manager.key, WrittenLibrary()))

        assert started_in.get_path(config_manager.key).exists()
        assert (library_manager.library_state(config_manager.key), library_manager.current_library_key) == (
            LibraryState.MISSING,
            None,
        )


class TestTheLibraryAConversionWaitsFor:
    """A conversion waits out a generation, then takes the library or gives the request up."""

    def test_a_generation_under_way_is_waited_out(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        _create_library_file(library_manager, config_manager.key)
        library_manager._creator = CreatorEndingItsRun(library_manager)

        readiness = library_manager.library_readiness(config_manager.get_library_directory(), config_manager.key)

        assert readiness == LibraryReadiness.PREPARING

    def test_a_library_on_disk_with_no_generation_is_ready(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        _create_library_file(library_manager, config_manager.key)

        readiness = library_manager.library_readiness(config_manager.get_library_directory(), config_manager.key)

        assert readiness == LibraryReadiness.READY

    def test_a_library_another_version_built_with_no_generation_is_missing(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        _create_earlier_library_file(library_manager, config_manager.key)

        readiness = library_manager.library_readiness(config_manager.get_library_directory(), config_manager.key)

        assert readiness == LibraryReadiness.MISSING

    def test_a_library_missing_with_no_generation_is_missing(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        readiness = library_manager.library_readiness(config_manager.get_library_directory(), config_manager.key)

        assert readiness == LibraryReadiness.MISSING


class CreatorEndingItsRun:
    """A creator that notes whether its generation still read as in progress while it ended."""

    def __init__(self, manager: InstructionsLibraryManager) -> None:
        self._manager = manager
        self.generating_while_ending: List[bool] = []

    def shutdown(self) -> None:
        self.generating_while_ending.append(self._manager.is_generating())


class TestReleasingTheCreator:
    """A generation reads as in progress until its creator has ended the pool it ran on."""

    def test_the_generation_reads_as_in_progress_until_the_creator_has_ended(
        self,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        creator = CreatorEndingItsRun(library_manager)
        library_manager._creator = creator

        library_manager.release_creator()

        assert (creator.generating_while_ending, library_manager.is_generating()) == ([True], False)
