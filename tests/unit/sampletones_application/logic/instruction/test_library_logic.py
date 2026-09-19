import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Final, List
from unittest.mock import MagicMock, patch

import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.logic.instruction import library_manager as library_manager_module
from sampletones_application.logic.instruction.library import LibraryLogic
from sampletones_application.logic.instruction.library_manager import (
    InstructionsLibraryManager,
)
from sampletones_application.paths import LANG_EN
from sampletones_application.view_model.instruction.library import (
    LibraryPanelViewModel,
)
from sampletones_core.library import LibraryState
from sampletones_core.parallelization import TaskStatus
from sampletones_shared.exceptions import (
    DeserializationError,
    IncompatibleLibraryDataVersionError,
    InvalidLibraryDataError,
    InvalidLibraryDataValuesError,
    InvalidMetadataError,
    LoadLibraryError,
    UnhandledLibraryError,
)
from tests.suite.application import HeldQueue
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.language import FakeLanguageManager
from tests.suite.library import OTHER_LIBRARIES, WrittenLibrary, aim_library_directory

LOAD_ERROR_KEY: Final[str] = "instructions.library.message.status_load_error"
FILE_NOT_FOUND_KEY: Final[str] = "instructions.library.message.status_file_not_found"
FILE_LOAD_ERROR_KEY: Final[str] = "instructions.library.message.status_file_load_error"
INVALID_METADATA_KEY: Final[str] = "global.dialog.message.invalid_metadata_error"
INVALID_DATA_VALUES_KEY: Final[str] = "instructions.library.message.status_invalid_data_values"
INVALID_DATA_KEY: Final[str] = "instructions.library.message.status_invalid_data"
DESERIALIZATION_ERROR_KEY: Final[str] = "instructions.library.message.status_deserialization_error"
INCOMPATIBLE_VERSION_KEY: Final[str] = "instructions.library.template.incompatible_version_template"
GENERATION_CANCELED_KEY: Final[str] = "instructions.library.message.status_generation_canceled"
GENERATED_INSTRUCTIONS: Final[int] = 8

TEXTS: Final[Dict[str, str]] = {
    INCOMPATIBLE_VERSION_KEY: "got {} expected {}",
    "instructions.library.message.status_saving": "saving",
    "instructions.library.message.status_generation_failed": "failed",
    GENERATION_CANCELED_KEY: "canceled",
    "instructions.library.label.generate_library_button": "Generate",
    "instructions.library.label.regenerate_library_button": "Regenerate",
    "instructions.library.template.library_loaded_template": "{} loaded.",
    "instructions.library.template.library_exists_template": "{} exists.",
    "instructions.library.template.library_outdated_template": "{} was built by another version.",
    "instructions.library.template.library_not_exists_template": "{} doesn't exist.",
}


def _logic(*, operation_active: bool) -> LibraryLogic:
    """A library logic with only the state ``request_generation`` touches, bypassing the heavy
    constructor."""
    logic = LibraryLogic.__new__(LibraryLogic)
    logic._is_operation_active = lambda: operation_active
    logic.generate_library = MagicMock()
    return logic


def _preparing_logic(state: LibraryState) -> LibraryLogic:
    """A library logic whose configuration names a library standing as ``state``, bypassing the
    heavy constructor."""
    logic = LibraryLogic.__new__(LibraryLogic)
    logic._config_manager = MagicMock()
    logic._library_manager = MagicMock()
    logic._library_manager.library_state.return_value = state
    logic.generate_library = MagicMock()
    return logic


class TestPreparingTheLibraryForAConversion(BaseTestSuite):
    """A conversion uses a library this build reads as it stands; any other is generated."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        state: LibraryState
        expected: bool

    test_cases = (
        TestCase(label="a library this build reads", state=LibraryState.CURRENT, expected=False),
        TestCase(label="a library another version built", state=LibraryState.OUTDATED, expected=True),
        TestCase(label="no library", state=LibraryState.MISSING, expected=True),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_whether_it_is_generated(self, test_case: TestCase) -> None:
        logic = _preparing_logic(test_case.state)

        logic.prepare_library()

        assert logic.generate_library.called is test_case.expected


class TestRequestGeneration:
    """The user-initiated Generate path yields to an in-flight exclusive operation, so a standalone
    library generation cannot run alongside a conversion. A conversion's own preparatory generation
    bypasses this gate by calling ``generate_library`` directly."""

    def test_refuses_while_an_operation_is_active(self) -> None:
        logic = _logic(operation_active=True)
        logic.request_generation()
        logic.generate_library.assert_not_called()

    def test_generates_when_nothing_is_active(self) -> None:
        logic = _logic(operation_active=False)
        logic.request_generation()
        logic.generate_library.assert_called_once_with()


def _load_logic(*, load_error: Exception) -> LibraryLogic:
    """A library logic with only the state ``_load_library`` touches, bypassing the heavy
    constructor."""
    language_manager = FakeLanguageManager(TEXTS)
    logic = LibraryLogic.__new__(LibraryLogic)
    logic._is_locked_function = None
    logic._lock_function = None
    logic._unlock_function = MagicMock()
    logic._library_manager = MagicMock()
    logic._library_manager.load_library.side_effect = load_error
    logic._language_manager = language_manager
    logic._msg_load_error = language_manager[LOAD_ERROR_KEY]
    logic.on_load_error = MagicMock()
    return logic


class TestLoadLibraryTail:
    """The load pipeline wraps every unclassified deserialize failure in a ``LoadLibraryError``
    subtype, so the ladder's tail reports those through ``on_load_error`` with the generic
    message; a failure outside the load contract is a bug and propagates. Both paths unlock.
    """

    def test_unclassified_load_error_reports_the_generic_message(self) -> None:
        error = UnhandledLibraryError("wrapped")
        logic = _load_logic(load_error=error)

        logic._load_library(MagicMock())

        logic.on_load_error.assert_called_once_with(error, LOAD_ERROR_KEY)
        logic._unlock_function.assert_called_once_with()

    def test_unexpected_error_propagates_and_unlocks(self) -> None:
        logic = _load_logic(load_error=RuntimeError("bug"))

        with pytest.raises(RuntimeError):
            logic._load_library(MagicMock())

        logic.on_load_error.assert_not_called()
        logic._unlock_function.assert_called_once_with()


def _surfacing_load_logic(*, load_error: Exception) -> LibraryLogic:
    """A library logic wired with every callback the ``_load_library`` ladder reports through, so a
    concrete failure can be observed reaching the user-facing callbacks."""
    logic = _load_logic(load_error=load_error)
    logic.on_load_file_not_found = MagicMock()
    return logic


class TestLoadLibrarySurfacesConcreteErrors:
    """Each concrete load failure reaches the user through ``on_load_error`` with a populated
    message, so a bad library file is reported rather than swallowed. The library unlocks in
    every case."""

    @pytest.mark.parametrize(
        "error, expected_message",
        [
            (OSError("io"), FILE_LOAD_ERROR_KEY),
            (InvalidMetadataError("bad metadata"), INVALID_METADATA_KEY),
            (
                InvalidLibraryDataValuesError("bad values", ValueError("v")),
                INVALID_DATA_VALUES_KEY,
            ),
            (InvalidLibraryDataError("bad data"), INVALID_DATA_KEY),
            (DeserializationError("bad bytes"), DESERIALIZATION_ERROR_KEY),
            (LoadLibraryError("unclassified"), LOAD_ERROR_KEY),
        ],
    )
    def test_concrete_error_reports_populated_message(
        self,
        error: Exception,
        expected_message: str,
    ) -> None:
        logic = _surfacing_load_logic(load_error=error)

        logic._load_library(MagicMock())

        logic.on_load_error.assert_called_once_with(error, expected_message)
        logic._unlock_function.assert_called_once_with()

    def test_missing_file_reports_through_file_not_found_callback(self) -> None:
        logic = _surfacing_load_logic(load_error=FileNotFoundError("gone"))

        logic._load_library(MagicMock())

        logic.on_load_file_not_found.assert_called_once_with(
            logic._library_manager.get_path.return_value,
            FILE_NOT_FOUND_KEY,
        )
        logic.on_load_error.assert_not_called()
        logic._unlock_function.assert_called_once_with()

    def test_incompatible_version_reports_both_versions(self) -> None:
        error = IncompatibleLibraryDataVersionError(
            "mismatch",
            expected_version="2.0",
            actual_version="9.0",
        )
        logic = _surfacing_load_logic(load_error=error)

        logic._load_library(MagicMock())

        logic.on_load_error.assert_called_once_with(error, "got 9.0 expected 2.0")
        logic._unlock_function.assert_called_once_with()


def _generation_logic(*, generating: bool = True) -> LibraryLogic:
    """A library logic with only the state the generation emits touch, bypassing the heavy
    constructor."""
    logic = LibraryLogic.__new__(LibraryLogic)
    logic._config_manager = MagicMock()
    logic._library_manager = MagicMock()
    logic._library_manager.is_generating.return_value = generating
    logic._library_manager.is_library_loaded.return_value = False
    logic._library_manager.library_state.return_value = LibraryState.MISSING
    logic._language_manager = FakeLanguageManager(TEXTS)
    logic.on_view_changed = MagicMock()
    return logic


class TestGenerationEmits:
    """Every emit passes its status and progress explicitly, so the logic retains no
    presentation state between emissions and each view model is complete on its own."""

    def test_canceled_emits_the_language_managed_status(self) -> None:
        logic = _generation_logic()

        logic._on_generation_progress(TaskStatus.CANCELED, MagicMock())

        view_model = logic.on_view_changed.call_args.args[0]
        assert view_model.status_text == "canceled"

    def test_completed_emits_saving_at_full_progress(self) -> None:
        logic = _generation_logic()

        logic._on_generation_progress(TaskStatus.COMPLETED, MagicMock())

        view_model = logic.on_view_changed.call_args.args[0]
        assert view_model.status_text == "saving"
        assert view_model.progress_value == 1.0
        assert view_model.progress_overlay == "100%"

    def test_failed_emits_the_failure_status(self) -> None:
        logic = _generation_logic()

        logic._on_generation_progress(TaskStatus.FAILED, MagicMock())

        view_model = logic.on_view_changed.call_args.args[0]
        assert view_model.status_text == "failed"
        assert view_model.progress_value == 0.0

    def test_update_status_yields_during_generation(self) -> None:
        logic = _generation_logic(generating=True)

        logic.update_status()

        logic.on_view_changed.assert_not_called()

    def test_update_status_repaints_the_idle_state(self) -> None:
        logic = _generation_logic(generating=False)

        with patch(
            "sampletones_application.logic.instruction.library.get_display_name_from_key",
            return_value="lib",
        ):
            logic.update_status()

        view_model = logic.on_view_changed.call_args.args[0]
        assert view_model.status_text == "lib doesn't exist."
        assert view_model.is_generating is False

    def test_update_status_reports_a_loaded_library(self) -> None:
        logic = _generation_logic(generating=False)
        logic._library_manager.is_library_loaded.return_value = True

        with patch(
            "sampletones_application.logic.instruction.library.get_display_name_from_key",
            return_value="lib",
        ):
            logic.update_status()

        view_model = logic.on_view_changed.call_args.args[0]
        assert view_model.status_text == "lib loaded."
        assert view_model.generate_button_label == "Regenerate"

    def test_update_status_reports_a_library_another_version_built(self) -> None:
        logic = _generation_logic(generating=False)
        logic._library_manager.library_state.return_value = LibraryState.OUTDATED

        with patch(
            "sampletones_application.logic.instruction.library.get_display_name_from_key",
            return_value="lib",
        ):
            logic.update_status()

        view_model = logic.on_view_changed.call_args.args[0]
        assert view_model.status_text == "lib was built by another version."

    def test_update_status_reports_an_existing_unloaded_library(self) -> None:
        logic = _generation_logic(generating=False)
        logic._library_manager.library_state.return_value = LibraryState.CURRENT

        with patch(
            "sampletones_application.logic.instruction.library.get_display_name_from_key",
            return_value="lib",
        ):
            logic.update_status()

        view_model = logic.on_view_changed.call_args.args[0]
        assert view_model.status_text == "lib exists."
        assert view_model.generate_button_label == "Generate"


class TreeLock:
    """The lock the catalog's tree shares with a generation, counted the way the tree counts it."""

    def __init__(self) -> None:
        self.holders = 0

    def lock(self) -> None:
        self.holders += 1

    def unlock(self) -> None:
        self.holders = max(0, self.holders - 1)

    def locked(self) -> bool:
        return self.holders > 0


class Creator:
    """A library creator whose workers have finished, holding the reports it was handed."""

    total_instructions = GENERATED_INSTRUCTIONS
    completed_instructions = GENERATED_INSTRUCTIONS

    def __init__(self, _config: Any, _window: Any) -> None:
        self.callbacks: Dict[str, Callable[..., None]] = {}

    def set_callbacks(self, **callbacks: Callable[..., None]) -> None:
        self.callbacks.update(callbacks)

    def start(self) -> None:
        pass

    def shutdown(self) -> None:
        pass


@dataclass
class Catalog:
    """A library logic over a real catalog, with what it hands the tab written down."""

    logic: LibraryLogic
    manager: InstructionsLibraryManager
    config_manager: ConfigManager
    queue: HeldQueue
    lock: TreeLock
    rebuilds_under_lock: List[bool] = field(default_factory=list)
    views: List[LibraryPanelViewModel] = field(default_factory=list)

    @property
    def creator(self) -> Creator:
        creator = self.manager.creator
        assert isinstance(creator, Creator)
        return creator

    def start_generation(self) -> None:
        """Ask for a generation and take the start report its creator sends."""
        self.logic.generate_library()
        self.creator.callbacks["on_start"]()
        self.queue.drain()

    def write_library(self) -> None:
        """Report the library complete from a thread of its own, as a creator's monitor does."""
        worker = threading.Thread(
            target=self.creator.callbacks["on_completed"],
            args=((self.config_manager.key, WrittenLibrary()),),
        )
        worker.start()
        worker.join()


@pytest.fixture
def catalog(
    config_manager: ConfigManager,
    held_queue: HeldQueue,
    monkeypatch: pytest.MonkeyPatch,
) -> Catalog:
    monkeypatch.setattr(library_manager_module, "InstructionsLibraryCreator", Creator)
    manager = InstructionsLibraryManager(config_manager, language_manager=MagicMock())
    logic = LibraryLogic(
        config_manager,
        manager,
        language_manager=FakeLanguageManager(TEXTS),
        is_operation_active=lambda: False,
    )
    lock = TreeLock()
    logic.configure_lock(lock.lock, lock.unlock, lock.locked)
    config_manager.add_config_change_callback(logic.follow_config)
    catalog = Catalog(logic=logic, manager=manager, config_manager=config_manager, queue=held_queue, lock=lock)
    logic.on_rebuild_tree_needed = lambda: catalog.rebuilds_under_lock.append(lock.locked())
    logic.on_view_changed = catalog.views.append
    return catalog


def _complete(catalog: Catalog) -> None:
    catalog.write_library()


def _cancel(catalog: Catalog) -> None:
    catalog.creator.callbacks["on_progress"](TaskStatus.CANCELED, MagicMock())
    catalog.creator.callbacks["on_canceled"]()


def _fail(catalog: Catalog) -> None:
    catalog.creator.callbacks["on_error"](RuntimeError("generation failed"))


ENDINGS: Final = pytest.mark.parametrize(
    "ending",
    [_complete, _cancel, _fail],
    ids=["completed", "canceled", "failed"],
)


class TestAGenerationClosing:
    """A generation reports from the creator's threads, and the render loop takes each report up:
    the close lets the tree lock go, then reads the catalog the library was written into."""

    def test_the_lock_is_taken_when_the_generation_is_asked_for(self, catalog: Catalog) -> None:
        catalog.logic.generate_library()

        assert (catalog.manager.is_generating(), catalog.lock.locked()) == (True, True)

    def test_the_close_waits_for_the_render_loop(self, catalog: Catalog) -> None:
        catalog.start_generation()

        catalog.write_library()

        assert (catalog.manager.is_generating(), catalog.lock.locked(), catalog.rebuilds_under_lock) == (
            True,
            True,
            [],
        )

    def test_the_tree_is_rebuilt_once_the_lock_is_let_go(self, catalog: Catalog) -> None:
        catalog.start_generation()
        catalog.write_library()

        catalog.queue.drain()

        assert catalog.rebuilds_under_lock == [False]

    def test_the_library_written_reads_as_loaded(self, catalog: Catalog) -> None:
        catalog.start_generation()
        catalog.write_library()

        catalog.queue.drain()

        assert catalog.logic.is_library_loaded(catalog.config_manager.key) is True
        assert catalog.views[-1].generate_button_label == "Regenerate"

    @ENDINGS
    def test_every_ending_paints_the_idle_controls(self, catalog: Catalog, ending: Any) -> None:
        catalog.start_generation()

        ending(catalog)
        catalog.queue.drain()

        assert (catalog.manager.is_generating(), catalog.views[-1].is_generating, catalog.lock.locked()) == (
            False,
            False,
            False,
        )


class TestTheCatalogFollowingTheConfiguration:
    """A configuration change naming another library directory roots the catalog there, and any
    other change repaints the status over the libraries already loaded."""

    def test_another_directory_is_read_afresh(self, catalog: Catalog, tmp_path: Path) -> None:
        other = tmp_path / OTHER_LIBRARIES

        aim_library_directory(catalog.config_manager, other)

        assert (catalog.manager.library_directory, catalog.rebuilds_under_lock) == (other, [False])

    def test_the_same_directory_repaints_over_what_is_loaded(self, catalog: Catalog) -> None:
        catalog.manager._library.save_data(catalog.config_manager.key, WrittenLibrary())

        aim_library_directory(catalog.config_manager, catalog.config_manager.get_library_directory())

        assert catalog.rebuilds_under_lock == []
        assert catalog.views[-1].generate_button_label == "Regenerate"

    @ENDINGS
    def test_a_change_during_a_generation_stands_whatever_the_generation_came_to(
        self,
        catalog: Catalog,
        ending: Any,
        tmp_path: Path,
    ) -> None:
        other = tmp_path / OTHER_LIBRARIES
        catalog.start_generation()

        aim_library_directory(catalog.config_manager, other)
        ending(catalog)
        catalog.queue.drain()

        assert catalog.manager.library_directory == catalog.config_manager.get_library_directory() == other

    def test_a_library_generated_across_a_change_lands_where_the_generation_started(
        self,
        catalog: Catalog,
        tmp_path: Path,
    ) -> None:
        started_in = catalog.config_manager.get_library_directory()
        catalog.start_generation()

        aim_library_directory(catalog.config_manager, tmp_path / OTHER_LIBRARIES)
        catalog.write_library()
        catalog.queue.drain()

        assert (started_in / catalog.config_manager.key.filename).exists()
        assert catalog.manager.library_state(catalog.config_manager.key) is LibraryState.MISSING


class TestCanceledStatusLanguageKey:
    """The canceled status resolves through ``LanguageManager`` at construction, so the language
    file must carry the key."""

    def test_canceled_status_resolves_from_the_language_file(self) -> None:
        language_manager = LanguageManager(LANG_EN)

        assert language_manager[GENERATION_CANCELED_KEY]
