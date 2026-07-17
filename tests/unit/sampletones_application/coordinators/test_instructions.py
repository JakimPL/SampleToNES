from pathlib import Path
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


def _remove_library_coordinator(*, current_library_key: object | None) -> InstructionsTabCoordinator:
    coordinator = InstructionsTabCoordinator.__new__(InstructionsTabCoordinator)
    coordinator._library_logic = MagicMock()
    coordinator._library_logic.current_library_key = current_library_key
    coordinator._dialogs = MagicMock()
    coordinator._instruction_player_logic = MagicMock()
    coordinator._on_audio_state_changed = MagicMock()
    coordinator._close_instruction = MagicMock()
    coordinator._instruction_details_logic = MagicMock()
    coordinator._ttl_remove_library = "Remove library"
    coordinator._msg_remove_library = "Remove this library?"
    coordinator._lbl_remove = "Remove"
    return coordinator


class TestRemoveLibrary:
    def test_request_prompts_confirmation(self) -> None:
        coordinator = _remove_library_coordinator(current_library_key="current")
        key = "current"
        coordinator._library_logic.get_path.return_value = Path("lead.stnlib")

        coordinator._request_remove_library(key)

        confirmation = coordinator._dialogs.show_confirmation.call_args.kwargs
        assert confirmation["message"] == "Remove this library?"
        assert confirmation["path"] == Path("lead.stnlib")

        confirmation["on_confirm"]()
        coordinator._library_logic.remove_library.assert_called_once_with(key)

    def test_removing_current_library_clears_display_and_audio(self) -> None:
        key = "current"
        coordinator = _remove_library_coordinator(current_library_key=key)
        coordinator._instruction_details_logic.get_current_instruction_data.return_value = MagicMock(library_key=key)

        coordinator._remove_library(key)

        coordinator._close_instruction.assert_called_once_with()
        coordinator._instruction_player_logic.clear_audio.assert_not_called()
        coordinator._on_audio_state_changed.assert_called_once_with()

    def test_removing_other_library_keeps_current_display(self) -> None:
        coordinator = _remove_library_coordinator(current_library_key="current")
        coordinator._instruction_details_logic.get_current_instruction_data.return_value = MagicMock(
            library_key="current"
        )

        coordinator._remove_library("other")

        coordinator._close_instruction.assert_not_called()
        coordinator._instruction_player_logic.clear_audio.assert_not_called()

    def test_removing_loaded_library_clears_display_even_after_selection_changed(self) -> None:
        coordinator = _remove_library_coordinator(current_library_key="other")
        coordinator._instruction_details_logic.get_current_instruction_data.return_value = MagicMock(
            library_key="removed"
        )

        coordinator._remove_library("removed")

        coordinator._close_instruction.assert_called_once_with()
        coordinator._instruction_player_logic.clear_audio.assert_not_called()


def _display_coordinator() -> InstructionsTabCoordinator:
    """A coordinator with only the collaborators ``_display_instruction`` touches, bypassing the
    heavy constructor."""
    coordinator = InstructionsTabCoordinator.__new__(InstructionsTabCoordinator)
    coordinator._waveform_panel = MagicMock()
    coordinator._spectrum_panel = MagicMock()
    coordinator._instruction_player_logic = MagicMock()
    coordinator._instruction_details_logic = MagicMock()
    return coordinator


class TestDisplayInstruction:
    """The audible fragment always matches the displayed one: rendering an instruction loads both
    displays and reloads the player from its fragment, while an empty selection clears the displays
    and leaves the player alone."""

    def test_instruction_renders_and_reloads_the_player(self) -> None:
        coordinator = _display_coordinator()
        instruction_data = MagicMock()

        with patch("sampletones_application.coordinators.instructions.AudioData") as audio_data_cls:
            coordinator._display_instruction(instruction_data)

        coordinator._waveform_panel.load_library_fragment.assert_called_once_with(instruction_data.fragment)
        coordinator._spectrum_panel.load_library_fragment.assert_called_once_with(
            instruction_data.fragment,
            instruction_data.config.sample_rate,
            instruction_data.config.window_size,
        )
        audio_data_cls.from_library_fragment.assert_called_once_with(
            instruction_data.fragment,
            instruction_data.config.sample_rate,
        )
        coordinator._instruction_player_logic.load_audio_data.assert_called_once_with(
            audio_data_cls.from_library_fragment.return_value
        )

    def test_empty_selection_clears_the_displays_and_leaves_the_player_alone(self) -> None:
        coordinator = _display_coordinator()

        coordinator._display_instruction(None)

        coordinator._waveform_panel.clear_layers.assert_called_once_with()
        coordinator._spectrum_panel.clear_layers.assert_called_once_with()
        coordinator._instruction_details_logic.clear_display.assert_called_once_with()
        coordinator._instruction_player_logic.clear_audio.assert_called_once_with()
        coordinator._instruction_player_logic.load_audio_data.assert_not_called()


def _close_coordinator() -> InstructionsTabCoordinator:
    coordinator = InstructionsTabCoordinator.__new__(InstructionsTabCoordinator)
    coordinator._waveform_panel = MagicMock()
    coordinator._spectrum_panel = MagicMock()
    coordinator._instruction_details_logic = MagicMock()
    coordinator._instruction_player_logic = MagicMock()
    return coordinator


class TestCloseInstruction:
    def test_close_clears_graphs_details_and_audio(self) -> None:
        coordinator = _close_coordinator()

        coordinator._close_instruction()

        coordinator._waveform_panel.clear_layers.assert_called_once_with()
        coordinator._spectrum_panel.clear_layers.assert_called_once_with()
        coordinator._instruction_details_logic.clear_display.assert_called_once_with()
        coordinator._instruction_player_logic.clear_audio.assert_called_once_with()


def _render_coordinator(*, plot_error: Exception) -> InstructionsTabCoordinator:
    """A coordinator with only the displays ``_render_instruction`` touches, bypassing the heavy
    constructor."""
    coordinator = InstructionsTabCoordinator.__new__(InstructionsTabCoordinator)
    coordinator._waveform_panel = MagicMock()
    coordinator._waveform_panel.load_library_fragment.side_effect = plot_error
    coordinator._spectrum_panel = MagicMock()
    return coordinator


class TestRenderInstructionClassification:
    """Rendering classification guard: a data-shape failure that makes the fragment unplottable
    re-raises as ``LibraryDisplayError`` for ``_on_instruction_loaded`` to catch; a failure outside
    those types is a bug and propagates."""

    @pytest.mark.parametrize(
        "error",
        [KeyError("generator"), IndexError("empty histogram"), ValueError("degenerate data")],
        ids=["key", "index", "value"],
    )
    def test_data_shape_failure_raises_library_display_error(self, error: Exception) -> None:
        coordinator = _render_coordinator(plot_error=error)

        with pytest.raises(LibraryDisplayError) as excinfo:
            coordinator._render_instruction(MagicMock())

        assert excinfo.value.__cause__ is error

    def test_unexpected_failure_propagates(self) -> None:
        coordinator = _render_coordinator(plot_error=RuntimeError("bug"))

        with pytest.raises(RuntimeError):
            coordinator._render_instruction(MagicMock())


def _loaded_coordinator(*, display_error: Exception) -> InstructionsTabCoordinator:
    """A coordinator with only the collaborators ``_on_instruction_loaded`` touches, bypassing
    the heavy constructor."""
    coordinator = InstructionsTabCoordinator.__new__(InstructionsTabCoordinator)
    coordinator._waveform_panel = MagicMock()
    coordinator._waveform_panel.load_library_fragment.side_effect = display_error
    coordinator._spectrum_panel = MagicMock()
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
