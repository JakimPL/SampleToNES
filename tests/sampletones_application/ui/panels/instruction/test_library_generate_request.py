from unittest.mock import MagicMock

from sampletones_application.ui.panels.instruction.library import (
    GUIInstructionsLibraryPanel,
)


def _panel(*, library_exists: bool) -> GUIInstructionsLibraryPanel:
    """A panel with only the state ``request_generate_library`` touches, bypassing the DearPyGui
    constructor."""
    panel = GUIInstructionsLibraryPanel.__new__(GUIInstructionsLibraryPanel)
    panel.library_logic = MagicMock()
    panel.library_logic.library_available_for_config.return_value = library_exists
    panel._dialogs = MagicMock()
    panel._msg_regenerate_confirmation = "message"
    panel._ttl_regenerate_confirmation = "title"
    panel._lbl_regenerate_confirmation_ok = "Regenerate"
    return panel


class TestGenerateRequest:
    """A library is rarely worth regenerating, so an existing one prompts for confirmation before the
    work starts; a missing one generates straight away."""

    def test_existing_library_asks_for_confirmation(self) -> None:
        panel = _panel(library_exists=True)

        panel.request_generate_library()

        panel.library_logic.request_generation.assert_not_called()
        panel._dialogs.show_confirmation.assert_called_once()
        _, kwargs = panel._dialogs.show_confirmation.call_args
        assert panel._dialogs.show_confirmation.call_args.args[3] is panel.library_logic.request_generation

    def test_missing_library_generates_immediately(self) -> None:
        panel = _panel(library_exists=False)

        panel.request_generate_library()

        panel._dialogs.show_confirmation.assert_not_called()
        panel.library_logic.request_generation.assert_called_once_with()
