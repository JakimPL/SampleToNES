from pathlib import Path
from unittest.mock import MagicMock

from sampletones_application.constants.main import (
    TAG_MAIN_EXPLORER_DIALOG_CONVERTER_RUNNING,
)
from sampletones_application.coordinators.main import MainTabCoordinator


def _coordinator(*, operation_active: bool) -> MainTabCoordinator:
    """A coordinator with only the state the reconstruct guards touch, bypassing the heavy
    constructor."""
    coordinator = MainTabCoordinator.__new__(MainTabCoordinator)
    coordinator._is_operation_active = lambda: operation_active
    coordinator._dialogs = MagicMock()
    coordinator._msg_converter_running = "running"
    coordinator._ttl_converter_running = "title"
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
            "running",
            "title",
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


class TestConversionSuccessDialog:
    """The completed-conversion notice interrupts deliberately: it is raised modal so it is
    acknowledged before further input."""

    def test_success_shows_the_modal_info_dialog(self) -> None:
        coordinator = MainTabCoordinator.__new__(MainTabCoordinator)
        coordinator._dialogs = MagicMock()
        coordinator._converter_panel = MagicMock()
        coordinator._converter_panel.tag = "converter.panel"
        coordinator._msg_success = "success"
        coordinator._ttl_progress = "title"

        coordinator._on_conversion_success()

        coordinator._dialogs.show_info.assert_called_once_with(
            "converter.panel",
            "success",
            "title",
            modal=True,
        )
