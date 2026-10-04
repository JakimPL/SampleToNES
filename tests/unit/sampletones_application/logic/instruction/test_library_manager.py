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
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.library import InstructionLibraryKey, LibraryState
from sampletones_core.structures.tree import LibraryNode
from tests.suite.compatibility import LIBRARY_VERSION, archived
from tests.suite.files import requires_symlinks
from tests.suite.library import LINKED_LIBRARIES, OTHER_LIBRARIES, WrittenLibrary, write_empty_library


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


class TestTheLibrariesTheCatalogLists:
    def test_a_library_another_version_built_is_marked_and_holds_no_generators(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        """A library another version built opens only to be rebuilt, so it lists nothing to load."""
        _set_transformation_gamma(config_manager, 50)
        earlier_key = config_manager.key
        _create_earlier_library_file(library_manager, earlier_key)
        _set_transformation_gamma(config_manager, 100)
        _create_library_file(library_manager, config_manager.key)

        library_manager.gather_available_libraries()
        library_manager.rebuild_tree()

        root = library_manager.tree.get_root()
        assert root is not None
        rows = {
            node.library_key: (node.outdated, len(node.children))
            for node in root.children
            if isinstance(node, LibraryNode)
        }
        assert rows == {earlier_key: (True, 0), config_manager.key: (False, len(GeneratorName))}


class TestTheDirectoryTheCatalogStandsAt:
    """The folder the catalog stands at keeps the libraries it loaded. A folder left lets them go and keeps
    the one it took up, so the reader coming back finds that choice again."""

    @staticmethod
    def _loaded_here(library_manager: InstructionsLibraryManager, key: InstructionLibraryKey) -> None:
        """Writes the library ``key`` names into the directory the catalog stands at, and loads it."""
        _create_library_file(library_manager, key)
        library_manager.load_library(key)

    def test_the_directory_it_stands_at_keeps_what_it_loaded(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        self._loaded_here(library_manager, config_manager.key)

        moved = library_manager.set_library_directory(config_manager.get_library_directory())

        assert (moved, library_manager.is_library_loaded(config_manager.key)) == (False, True)

    def test_another_directory_starts_with_nothing_loaded_or_taken_up(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
        tmp_path: Path,
    ) -> None:
        self._loaded_here(library_manager, config_manager.key)
        other = tmp_path / OTHER_LIBRARIES

        moved = library_manager.set_library_directory(other)

        assert (
            moved,
            library_manager.library_directory,
            library_manager.is_library_loaded(config_manager.key),
            library_manager.current_library_key,
        ) == (True, other, False, None)

    def test_pointing_away_lets_the_data_go_and_keeps_the_choice(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
        tmp_path: Path,
    ) -> None:
        """A folder left holds no library in memory, and the reader coming back finds its choice standing
        unloaded, for the catalog's logic to load again."""
        ours = config_manager.get_library_directory()
        self._loaded_here(library_manager, config_manager.key)
        left = library_manager._catalog

        library_manager.set_library_directory(tmp_path / OTHER_LIBRARIES)
        library_manager.gather_available_libraries()
        held_while_away = dict(left.library.data)
        library_manager.set_library_directory(ours)
        library_manager.gather_available_libraries()

        assert (
            held_while_away,
            library_manager.is_library_loaded(config_manager.key),
            library_manager.current_library_key,
        ) == ({}, False, config_manager.key)

    def test_what_the_other_directory_took_up_stays_with_it(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
        tmp_path: Path,
    ) -> None:
        ours = config_manager.get_library_directory()
        other = tmp_path / OTHER_LIBRARIES
        library_manager.set_library_directory(other)
        self._loaded_here(library_manager, config_manager.key)

        library_manager.set_library_directory(ours)

        assert (library_manager.is_library_loaded(config_manager.key), library_manager.current_library_key) == (
            False,
            None,
        )
        library_manager.set_library_directory(other)
        assert library_manager.current_library_key == config_manager.key

    def test_a_library_whose_file_left_while_away_is_let_go(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
        tmp_path: Path,
    ) -> None:
        ours = config_manager.get_library_directory()
        self._loaded_here(library_manager, config_manager.key)
        library_manager.set_library_directory(tmp_path / OTHER_LIBRARIES)
        library_manager.gather_available_libraries()
        (ours / config_manager.key.filename).unlink()

        library_manager.set_library_directory(ours)
        library_manager.gather_available_libraries()

        assert library_manager.is_library_loaded(config_manager.key) is False


class TestAnotherSpellingOfTheFolder:
    """Two spellings of one folder name one catalog, so pointing the catalog at another spelling keeps
    what the folder loaded and moves nowhere."""

    @staticmethod
    def _respelled_keeps_what_it_loaded(
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
        spelling: Path,
    ) -> None:
        _create_library_file(library_manager, config_manager.key)
        library_manager.load_library(config_manager.key)

        moved = library_manager.set_library_directory(spelling)

        assert (moved, library_manager.is_library_loaded(config_manager.key)) == (False, True)

    def test_a_detour_through_the_parent(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        folder = config_manager.get_library_directory()
        detour = folder.parent / ".." / folder.parent.name / folder.name

        self._respelled_keeps_what_it_loaded(config_manager, library_manager, detour)

    @requires_symlinks
    def test_a_link_to_the_folder(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
        tmp_path: Path,
    ) -> None:
        link = tmp_path / LINKED_LIBRARIES
        link.symlink_to(config_manager.get_library_directory(), target_is_directory=True)

        self._respelled_keeps_what_it_loaded(config_manager, library_manager, link)


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
        catalog = MagicMock()
        catalog.library.write_data.side_effect = PermissionError("save failed")
        error_callback = MagicMock()
        completed_callback = MagicMock()
        library_manager.on_generation_error = error_callback
        library_manager.on_generation_completed = completed_callback

        with pytest.raises(PermissionError):
            library_manager._complete_generation(catalog, (MagicMock(), MagicMock()))

        error_callback.assert_called_once()
        completed_callback.assert_not_called()

    def test_unexpected_error_propagates_directly(
        self,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        catalog = MagicMock()
        catalog.library.write_data.side_effect = RuntimeError("unexpected")
        error_callback = MagicMock()
        library_manager.on_generation_error = error_callback

        with pytest.raises(RuntimeError):
            library_manager._complete_generation(catalog, (MagicMock(), MagicMock()))

        error_callback.assert_not_called()

    def test_successful_save_sets_current_key_and_completes(
        self,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        library_manager._catalog.library = MagicMock()
        completed_callback = MagicMock()
        library_manager.on_generation_completed = completed_callback
        key = MagicMock()

        library_manager._complete_generation(library_manager._catalog, (key, MagicMock()))

        assert library_manager.current_library_key is key
        completed_callback.assert_called_once()

    def test_a_library_lands_where_its_generation_started(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
        tmp_path: Path,
    ) -> None:
        started_in = library_manager._catalog
        library_manager.set_library_directory(tmp_path / OTHER_LIBRARIES)

        library_manager._complete_generation(started_in, (config_manager.key, WrittenLibrary()))

        assert started_in.library.get_path(config_manager.key).exists()
        assert (library_manager.library_state(config_manager.key), library_manager.current_library_key) == (
            LibraryState.MISSING,
            None,
        )

    def test_a_library_generated_while_away_is_written_and_chosen_and_held_nowhere(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
        tmp_path: Path,
    ) -> None:
        """The folder the generation started in is left, so it keeps the library's file and its choice and
        no data, and the reader coming back finds the library chosen there."""
        ours = config_manager.get_library_directory()
        started_in = library_manager._catalog
        library_manager.set_library_directory(tmp_path / OTHER_LIBRARIES)

        library_manager._complete_generation(started_in, (config_manager.key, WrittenLibrary()))
        library_manager.set_library_directory(ours)

        assert (
            started_in.library.get_path(config_manager.key).exists(),
            started_in.library.data,
            library_manager.current_library_key,
        ) == (True, {}, config_manager.key)


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
