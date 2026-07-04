from unittest.mock import MagicMock

import pytest

from sampletones_application.logic.instruction.library import LibraryLogic
from sampletones_shared.exceptions import UnhandledLibraryError


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
