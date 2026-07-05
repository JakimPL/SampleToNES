from unittest.mock import MagicMock, patch

import pytest

from sampletones_application.coordinators.instructions import InstructionsTabCoordinator
from sampletones_shared.exceptions import LibraryDisplayError


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


def _generation_coordinator(*, converter_visible: bool) -> InstructionsTabCoordinator:
    """A coordinator with only the state the generation-completed notice touches, bypassing the
    heavy constructor."""
    coordinator = InstructionsTabCoordinator.__new__(InstructionsTabCoordinator)
    coordinator._is_converter_visible = lambda: converter_visible
    coordinator._dialogs = MagicMock()
    coordinator._msg_generation_success = "success"
    coordinator._ttl_generation_status = "title"
    return coordinator


class TestGenerationCompletedNotice:
    """The conversion flow generates libraries as a preparatory step and owns its own messaging,
    so the success notice appears only for a standalone generation."""

    def test_standalone_generation_shows_the_success_notice(self) -> None:
        coordinator = _generation_coordinator(converter_visible=False)

        coordinator._on_generation_completed()

        coordinator._dialogs.show_info.assert_called_once()

    def test_conversion_driven_generation_stays_silent(self) -> None:
        coordinator = _generation_coordinator(converter_visible=True)

        coordinator._on_generation_completed()

        coordinator._dialogs.show_info.assert_not_called()


def _display_coordinator() -> InstructionsTabCoordinator:
    """A coordinator with only the collaborators ``_display_instruction`` touches, bypassing the
    heavy constructor."""
    coordinator = InstructionsTabCoordinator.__new__(InstructionsTabCoordinator)
    coordinator._instruction_panel = MagicMock()
    coordinator._instruction_player_logic = MagicMock()
    return coordinator


class TestDisplayInstruction:
    """The audible fragment always matches the displayed one: rendering an instruction reloads
    the player from its fragment, and an empty selection renders while leaving the player alone."""

    def test_instruction_renders_and_reloads_the_player(self) -> None:
        coordinator = _display_coordinator()
        instruction_data = MagicMock()

        with patch("sampletones_application.coordinators.instructions.AudioData") as audio_data_cls:
            coordinator._display_instruction(instruction_data)

        coordinator._instruction_panel.display_instruction.assert_called_once_with(instruction_data)
        audio_data_cls.from_library_fragment.assert_called_once_with(
            instruction_data.fragment,
            instruction_data.config.sample_rate,
        )
        coordinator._instruction_player_logic.load_audio_data.assert_called_once_with(
            audio_data_cls.from_library_fragment.return_value
        )

    def test_empty_selection_renders_and_leaves_the_player_alone(self) -> None:
        coordinator = _display_coordinator()

        coordinator._display_instruction(None)

        coordinator._instruction_panel.display_instruction.assert_called_once_with(None)
        coordinator._instruction_player_logic.load_audio_data.assert_not_called()


def _loaded_coordinator(*, display_error: Exception) -> InstructionsTabCoordinator:
    """A coordinator with only the collaborators ``_on_instruction_loaded`` touches, bypassing
    the heavy constructor."""
    coordinator = InstructionsTabCoordinator.__new__(InstructionsTabCoordinator)
    coordinator._instruction_panel = MagicMock()
    coordinator._instruction_panel.display_instruction.side_effect = display_error
    coordinator._instruction_player_logic = MagicMock()
    coordinator._instruction_details_logic = MagicMock()
    coordinator._dialogs = MagicMock()
    coordinator._msg_display_error = "display error"
    coordinator._on_audio_state_changed = MagicMock()
    return coordinator


class TestInstructionLoadedRecovery:
    """This is the recovery boundary for the panel's rendering classification guard: a
    ``LibraryDisplayError`` becomes the display-error dialog and the audio state still
    refreshes; a failure outside that contract is a bug and propagates."""

    def test_display_error_shows_the_dialog_and_refreshes_audio_state(self) -> None:
        error = LibraryDisplayError("degenerate data")
        coordinator = _loaded_coordinator(display_error=error)

        coordinator._on_instruction_loaded(MagicMock())

        coordinator._dialogs.show_error.assert_called_once_with(error, "display error")
        coordinator._on_audio_state_changed.assert_called_once_with()

    def test_unexpected_error_propagates(self) -> None:
        coordinator = _loaded_coordinator(display_error=RuntimeError("bug"))

        with pytest.raises(RuntimeError):
            coordinator._on_instruction_loaded(MagicMock())

        coordinator._dialogs.show_error.assert_not_called()
