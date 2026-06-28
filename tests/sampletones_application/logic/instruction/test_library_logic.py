from unittest.mock import MagicMock

from sampletones_application.logic.instruction.library import LibraryLogic


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
