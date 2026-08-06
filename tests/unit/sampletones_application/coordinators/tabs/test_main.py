from pathlib import Path
from typing import Final
from unittest.mock import MagicMock

from sampletones_application.coordinators.tabs.main import MainTabCoordinator
from sampletones_application.logic.main.converter import ConversionSuccess
from sampletones_application.tags.main import (
    TAG_MAIN_CONVERTER_DIALOG_CANCEL,
    TAG_MAIN_CONVERTER_DIALOG_LOAD,
    TAG_MAIN_EXPLORER_DIALOG_CONVERTER_RUNNING,
)
from tests.suite.language import FakeLanguageManager

CONVERTER_RUNNING_MESSAGE_KEY: Final[str] = "main.explorer.message.converter_running_msg"
CONVERTER_RUNNING_TITLE_KEY: Final[str] = "main.explorer.title.converter_running_dialog"
LOAD_FILE_MESSAGE_KEY: Final[str] = "main.converter.message.load_file_prompt"
LOAD_BUTTON_KEY: Final[str] = "main.converter.label.load_button"
OPEN_BUTTON_KEY: Final[str] = "main.converter.label.open_button"
CLOSE_BUTTON_KEY: Final[str] = "main.converter.label.close_button"
STOP_BUTTON_KEY: Final[str] = "main.converter.label.stop_button"
CONTINUE_BUTTON_KEY: Final[str] = "main.converter.label.continue_button"


def _coordinator(*, operation_active: bool) -> MainTabCoordinator:
    """A coordinator with only the state the reconstruct guards touch, bypassing the heavy
    constructor."""
    coordinator = MainTabCoordinator.__new__(MainTabCoordinator)
    coordinator._is_operation_active = lambda: operation_active
    coordinator._dialogs = MagicMock()
    coordinator._language_manager = FakeLanguageManager()
    coordinator._on_reconstruct_file = MagicMock()
    coordinator._on_reconstruct_directory = MagicMock()
    return coordinator


class TestConverterRunningNotice:
    """The busy-authority guard at the intent entry point: an active exclusive operation raises
    the converter-running notice and reports the caller must decline; an idle authority stays
    silent so the caller proceeds."""

    def test_active_operation_notifies_and_reports_true(self) -> None:
        coordinator = _coordinator(operation_active=True)

        assert coordinator._notify_converter_running() is True

        coordinator._dialogs.show_info.assert_called_once_with(
            TAG_MAIN_EXPLORER_DIALOG_CONVERTER_RUNNING,
            CONVERTER_RUNNING_MESSAGE_KEY,
            CONVERTER_RUNNING_TITLE_KEY,
        )

    def test_idle_reports_false_silently(self) -> None:
        coordinator = _coordinator(operation_active=False)

        assert coordinator._notify_converter_running() is False

        coordinator._dialogs.show_info.assert_not_called()


class TestReconstructGuards:
    """Reconstruction and conversion share the exclusive worker pool, so the reconstruct intents
    decline while an operation runs and delegate to the wired callbacks when idle."""

    def test_file_request_declines_while_an_operation_is_active(self) -> None:
        coordinator = _coordinator(operation_active=True)

        coordinator._request_reconstruct_file(Path("/audio/sample.wav"))

        coordinator._on_reconstruct_file.assert_not_called()
        coordinator._dialogs.show_info.assert_called_once()

    def test_file_request_delegates_when_idle(self) -> None:
        coordinator = _coordinator(operation_active=False)
        filepath = Path("/audio/sample.wav")

        coordinator._request_reconstruct_file(filepath)

        coordinator._on_reconstruct_file.assert_called_once_with(filepath)
        coordinator._dialogs.show_info.assert_not_called()

    def test_directory_request_declines_while_an_operation_is_active(self) -> None:
        coordinator = _coordinator(operation_active=True)

        coordinator._request_reconstruct_directory(Path("/audio"))

        coordinator._on_reconstruct_directory.assert_not_called()
        coordinator._dialogs.show_info.assert_called_once()

    def test_directory_request_delegates_when_idle(self) -> None:
        coordinator = _coordinator(operation_active=False)
        directory = Path("/audio")

        coordinator._request_reconstruct_directory(directory)

        coordinator._on_reconstruct_directory.assert_called_once_with(directory)
        coordinator._dialogs.show_info.assert_not_called()


def _success_coordinator() -> MainTabCoordinator:
    coordinator = MainTabCoordinator.__new__(MainTabCoordinator)
    coordinator._dialogs = MagicMock()
    coordinator._on_refresh_trees = MagicMock()
    coordinator._converter_logic = MagicMock()
    coordinator._language_manager = FakeLanguageManager()
    return coordinator


class TestConversionSuccessDialog:
    """A completed conversion refreshes the reconstruction trees, then offers to load the result;
    both the load and the dismiss choice return the converter to idle."""

    def test_file_success_refreshes_and_offers_to_load(self) -> None:
        coordinator = _success_coordinator()
        output_path = Path("/reconstructions/kick.rcn")

        coordinator._on_conversion_success(ConversionSuccess(is_file=True, output_path=output_path))

        coordinator._on_refresh_trees.assert_called_once_with()
        coordinator._dialogs.show_confirmation.assert_called_once()
        args, kwargs = coordinator._dialogs.show_confirmation.call_args
        assert args[0] == TAG_MAIN_CONVERTER_DIALOG_LOAD
        assert args[1] == LOAD_FILE_MESSAGE_KEY
        assert args[3] == coordinator._converter_logic.handle_load_request
        assert kwargs["ok_label"] == LOAD_BUTTON_KEY
        assert kwargs["cancel_label"] == CLOSE_BUTTON_KEY
        assert kwargs["path"] == output_path
        assert kwargs["on_cancel"] == coordinator._converter_logic.close

    def test_directory_success_offers_to_open_without_a_path(self) -> None:
        coordinator = _success_coordinator()

        coordinator._on_conversion_success(ConversionSuccess(is_file=False, output_path=Path("/reconstructions")))

        _, kwargs = coordinator._dialogs.show_confirmation.call_args
        assert kwargs["ok_label"] == OPEN_BUTTON_KEY
        assert kwargs["path"] is None


class TestCancelConfirmation:
    """Cancelling is destructive, so the panel's cancel intent asks for confirmation before the
    conversion is actually stopped."""

    def test_cancel_request_confirms_before_stopping(self) -> None:
        coordinator = MainTabCoordinator.__new__(MainTabCoordinator)
        coordinator._dialogs = MagicMock()
        coordinator._converter_logic = MagicMock()
        coordinator._language_manager = FakeLanguageManager()

        coordinator._request_cancel_confirmation()

        coordinator._converter_logic.cancel.assert_not_called()
        coordinator._dialogs.show_confirmation.assert_called_once()
        args, kwargs = coordinator._dialogs.show_confirmation.call_args
        assert args[0] == TAG_MAIN_CONVERTER_DIALOG_CANCEL
        assert args[3] == coordinator._converter_logic.cancel
        assert kwargs["ok_label"] == STOP_BUTTON_KEY
        assert kwargs["cancel_label"] == CONTINUE_BUTTON_KEY
