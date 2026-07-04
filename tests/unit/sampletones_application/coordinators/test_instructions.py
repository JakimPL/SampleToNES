from unittest.mock import MagicMock

from sampletones_application.coordinators.instructions import InstructionsTabCoordinator


def _coordinator(*, library_exists: bool) -> InstructionsTabCoordinator:
    """A coordinator with only the state ``_request_generate_library`` touches, bypassing the
    constructor."""
    coordinator = InstructionsTabCoordinator.__new__(InstructionsTabCoordinator)
    coordinator._library_logic = MagicMock()
    coordinator._library_logic.library_available_for_config.return_value = library_exists
    coordinator._dialogs = MagicMock()
    coordinator._msg_regenerate_confirmation = "message"
    coordinator._ttl_regenerate_confirmation = "title"
    coordinator._lbl_regenerate_confirmation_ok = "Regenerate"
    return coordinator


class TestGenerateRequest:
    """A library is rarely worth regenerating, so an existing one prompts for confirmation before the
    work starts; a missing one generates straight away."""

    def test_existing_library_asks_for_confirmation(self) -> None:
        coordinator = _coordinator(library_exists=True)

        coordinator._request_generate_library()

        coordinator._library_logic.request_generation.assert_not_called()
        coordinator._dialogs.show_confirmation.assert_called_once()
        confirm_action = coordinator._dialogs.show_confirmation.call_args.args[3]
        assert confirm_action is coordinator._library_logic.request_generation

    def test_missing_library_generates_immediately(self) -> None:
        coordinator = _coordinator(library_exists=False)

        coordinator._request_generate_library()

        coordinator._dialogs.show_confirmation.assert_not_called()
        coordinator._library_logic.request_generation.assert_called_once_with()
