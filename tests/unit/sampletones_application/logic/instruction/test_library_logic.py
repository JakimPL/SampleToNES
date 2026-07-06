import threading
from unittest.mock import MagicMock, patch

import pytest

from sampletones_application.categories.elements.instructions import InstructionsLibraryElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.logic.instruction.library import LibraryLogic
from sampletones_application.paths import LANG_EN
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


def _logic(*, operation_active: bool) -> LibraryLogic:
    """A library logic with only the state ``request_generation`` touches, bypassing the heavy
    constructor."""
    logic = LibraryLogic.__new__(LibraryLogic)
    logic._is_operation_active = lambda: operation_active
    logic.generate_library = MagicMock()
    return logic


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
    logic = LibraryLogic.__new__(LibraryLogic)
    logic._is_locked_function = None
    logic._lock_function = None
    logic._unlock_function = MagicMock()
    logic._library_manager = MagicMock()
    logic._library_manager.load_library.side_effect = load_error
    logic._msg_load_error = "load error"
    logic.on_load_error = MagicMock()
    return logic


class TestLoadLibraryTail:
    """The load pipeline wraps every unclassified deserialize failure in a ``LoadLibraryError``
    subtype, so the ladder's tail reports those through ``on_load_error`` with the generic
    message; a failure outside the load contract is a bug and propagates. Both paths unlock."""

    def test_unclassified_load_error_reports_the_generic_message(self) -> None:
        error = UnhandledLibraryError("wrapped")
        logic = _load_logic(load_error=error)

        logic._load_library(MagicMock())

        logic.on_load_error.assert_called_once_with(error, "load error")
        logic._unlock_function.assert_called_once_with()

    def test_unexpected_error_propagates_and_unlocks(self) -> None:
        logic = _load_logic(load_error=RuntimeError("bug"))

        with pytest.raises(RuntimeError):
            logic._load_library(MagicMock())

        logic.on_load_error.assert_not_called()
        logic._unlock_function.assert_called_once_with()


def _surfacing_load_logic(*, load_error: Exception) -> LibraryLogic:
    """A library logic wired with every callback and message the ``_load_library`` ladder reports
    through, so a concrete failure can be observed reaching the user-facing callbacks."""
    logic = _load_logic(load_error=load_error)
    logic.on_load_file_not_found = MagicMock()
    logic._msg_file_not_found = "file not found"
    logic._msg_file_load_error = "file load error"
    logic._msg_invalid_metadata_error = "invalid metadata"
    logic._msg_invalid_data_values_error = "invalid values"
    logic._msg_invalid_data_error = "invalid data"
    logic._msg_deserialization_error = "deserialization error"
    logic._tpl_incompatible_version_error = "got {} expected {}"
    return logic


class TestLoadLibrarySurfacesConcreteErrors:
    """Each concrete load failure reaches the user through ``on_load_error`` with a populated
    message, so a bad library file is reported rather than swallowed. The library unlocks in
    every case."""

    @pytest.mark.parametrize(
        "error, expected_message",
        [
            (OSError("io"), "file load error"),
            (InvalidMetadataError("bad metadata"), "invalid metadata"),
            (InvalidLibraryDataValuesError("bad values", ValueError("v")), "invalid values"),
            (InvalidLibraryDataError("bad data"), "invalid data"),
            (DeserializationError("bad bytes"), "deserialization error"),
            (LoadLibraryError("unclassified"), "load error"),
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
            "file not found",
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
    logic._status_lock = threading.Lock()
    logic._config_manager = MagicMock()
    logic._library_manager = MagicMock()
    logic._library_manager.is_generating.return_value = generating
    logic._library_manager.is_library_loaded.return_value = False
    logic._lbl_generate_library = "Generate"
    logic._lbl_regenerate_library = "Regenerate"
    logic._msg_generation_saving = "saving"
    logic._msg_generation_failed = "failed"
    logic._msg_generation_cancelled = "cancelled"
    logic.on_view_changed = MagicMock()
    return logic


class TestGenerationEmits:
    """Every emit passes its status and progress explicitly, so the logic retains no
    presentation state between emissions and each view model is complete on its own."""

    def test_cancelled_emits_the_language_managed_status(self) -> None:
        logic = _generation_logic()

        logic._on_generation_progress(TaskStatus.CANCELLED, MagicMock())

        view_model = logic.on_view_changed.call_args.args[0]
        assert view_model.status_text == "cancelled"

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
        logic._library_manager.library_exists_for_key.return_value = False
        logic._tpl_not_exists = "{} doesn't exist."

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
        logic._tpl_library_loaded = "{} loaded."

        with patch(
            "sampletones_application.logic.instruction.library.get_display_name_from_key",
            return_value="lib",
        ):
            logic.update_status()

        view_model = logic.on_view_changed.call_args.args[0]
        assert view_model.status_text == "lib loaded."
        assert view_model.generate_button_label == "Regenerate"

    def test_update_status_reports_an_existing_unloaded_library(self) -> None:
        logic = _generation_logic(generating=False)
        logic._library_manager.library_exists_for_key.return_value = True
        logic._tpl_library_exists = "{} exists."

        with patch(
            "sampletones_application.logic.instruction.library.get_display_name_from_key",
            return_value="lib",
        ):
            logic.update_status()

        view_model = logic.on_view_changed.call_args.args[0]
        assert view_model.status_text == "lib exists."
        assert view_model.generate_button_label == "Generate"


class TestCancelledStatusLanguageKey:
    """The cancelled status resolves through ``LanguageManager`` at construction, so the language
    file must carry the key."""

    def test_cancelled_status_resolves_from_the_language_file(self) -> None:
        language_manager = LanguageManager(LANG_EN)

        text = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_GENERATION_CANCELLED,
        ]

        assert text
