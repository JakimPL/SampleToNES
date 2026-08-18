from pathlib import Path
from typing import Dict, Final
from unittest.mock import MagicMock

import pytest

from sampletones_application.categories.export import ExportMessages
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.coordinators.tabs.reconstruction import (
    ReconstructionTabCoordinator,
)
from sampletones_application.paths import LANG_EN
from sampletones_application.services.export.kind import ExportKind
from sampletones_application.services.export.success import ExportSuccess
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.trackers.format import TrackerFormat
from sampletones_shared.exceptions import (
    DeserializationError,
    IncompatibleReconstructionVersionError,
    InvalidMetadataError,
    InvalidReconstructionError,
    InvalidReconstructionValuesError,
    LoadReconstructionError,
    UnhandledReconstructionError,
)
from tests.suite.language import FakeLanguageManager

FILE_NOT_FOUND_KEY: Final[str] = "reconstructions.browser.message.file_not_found"
LOAD_ERROR_KEY: Final[str] = "reconstructions.browser.message.load_error"
INVALID_METADATA_KEY: Final[str] = "global.dialog.message.invalid_metadata_error"
INVALID_VALUES_KEY: Final[str] = "reconstructions.browser.message.invalid_values"
INVALID_FILE_KEY: Final[str] = "reconstructions.browser.message.invalid_file"
DESERIALIZATION_ERROR_KEY: Final[str] = "reconstructions.browser.message.deserialization_error"
INCOMPATIBLE_VERSION_KEY: Final[str] = "reconstructions.browser.template.incompatible_version_template"
REMOVE_RECONSTRUCTION_MESSAGE_KEY: Final[str] = "reconstructions.browser.message.remove_reconstruction_message"
REMOVE_DIRECTORY_MESSAGE_KEY: Final[str] = "reconstructions.browser.message.remove_directory_message"

TEXTS: Final[Dict[str, str]] = {INCOMPATIBLE_VERSION_KEY: "got {} expected {}"}


@pytest.fixture
def coordinator() -> ReconstructionTabCoordinator:
    """A coordinator with only the collaborators ``load_reconstruction`` touches, bypassing the
    heavy constructor."""
    instance = object.__new__(ReconstructionTabCoordinator)
    instance._browser_panel = MagicMock()
    instance._reconstruction_manager = MagicMock()
    instance._dialogs = MagicMock()
    instance._language_manager = FakeLanguageManager(TEXTS)
    instance._msg_load_error = LOAD_ERROR_KEY
    return instance


class TestLoadReconstructionSurfacesConcreteErrors:
    """Each concrete load failure reaches the user through a populated error dialog, so a bad
    reconstruction file is reported rather than swallowed. The browser unlocks in every case.
    """

    @pytest.mark.parametrize(
        "error, expected_message",
        [
            (InvalidMetadataError("bad metadata"), INVALID_METADATA_KEY),
            (
                InvalidReconstructionValuesError("bad values", ValueError("v")),
                INVALID_VALUES_KEY,
            ),
            (InvalidReconstructionError("bad file"), INVALID_FILE_KEY),
            (DeserializationError("bad bytes"), DESERIALIZATION_ERROR_KEY),
            (LoadReconstructionError("unclassified"), LOAD_ERROR_KEY),
            (OSError("io"), LOAD_ERROR_KEY),
        ],
    )
    def test_concrete_error_shows_populated_dialog(
        self,
        coordinator: ReconstructionTabCoordinator,
        error: Exception,
        expected_message: str,
    ) -> None:
        coordinator._reconstruction_manager.load_reconstruction.side_effect = error

        coordinator.load_reconstruction(Path("sample.stn"))

        coordinator._dialogs.show_error.assert_called_once_with(
            error,
            expected_message,
        )
        coordinator._browser_panel.unlock.assert_called_once_with()

    def test_missing_file_shows_file_not_found_dialog(
        self,
        coordinator: ReconstructionTabCoordinator,
    ) -> None:
        error = FileNotFoundError("gone")
        coordinator._reconstruction_manager.load_reconstruction.side_effect = error
        path = Path("sample.stn")

        coordinator.load_reconstruction(path)

        coordinator._dialogs.show_file_not_found.assert_called_once_with(
            path,
            FILE_NOT_FOUND_KEY,
        )
        coordinator._browser_panel.unlock.assert_called_once_with()

    def test_incompatible_version_dialog_reports_both_versions(
        self,
        coordinator: ReconstructionTabCoordinator,
    ) -> None:
        error = IncompatibleReconstructionVersionError(
            "mismatch",
            expected_version="2.0",
            actual_version="9.0",
        )
        coordinator._reconstruction_manager.load_reconstruction.side_effect = error

        coordinator.load_reconstruction(Path("sample.stn"))

        coordinator._dialogs.show_error.assert_called_once_with(error, "got 9.0 expected 2.0")
        coordinator._browser_panel.unlock.assert_called_once_with()


class TestLoadReconstructionTail:
    """The load pipeline wraps every unclassified deserialize failure in a
    ``LoadReconstructionError`` subtype, so the ladder's tail presents those with the generic
    load-error dialog; a failure outside the load contract is a bug and propagates. The browser
    unlocks either way."""

    def test_unclassified_load_error_shows_the_generic_dialog(
        self,
        coordinator: ReconstructionTabCoordinator,
    ) -> None:
        error = UnhandledReconstructionError("wrapped")
        coordinator._reconstruction_manager.load_reconstruction.side_effect = error

        coordinator.load_reconstruction(Path("sample.stn"))

        coordinator._dialogs.show_error.assert_called_once_with(
            error,
            LOAD_ERROR_KEY,
        )
        coordinator._browser_panel.unlock.assert_called_once_with()

    def test_unexpected_error_propagates_and_unlocks(
        self,
        coordinator: ReconstructionTabCoordinator,
    ) -> None:
        coordinator._reconstruction_manager.load_reconstruction.side_effect = RuntimeError("bug")

        with pytest.raises(RuntimeError):
            coordinator.load_reconstruction(Path("sample.stn"))

        coordinator._dialogs.show_error.assert_not_called()
        coordinator._browser_panel.unlock.assert_called_once_with()


class TestAudioDataChanged:
    """The reconstruction player mirrors the loaded reconstruction: fresh audio replaces the
    player's data and a cleared reconstruction empties the player."""

    def test_new_audio_loads_into_the_player(self) -> None:
        instance = object.__new__(ReconstructionTabCoordinator)
        instance._reconstruction_player_logic = MagicMock()
        audio_data = MagicMock()

        instance._on_audio_data_changed(audio_data)

        instance._reconstruction_player_logic.load_audio_data.assert_called_once_with(audio_data)
        instance._reconstruction_player_logic.clear_audio.assert_not_called()

    def test_cleared_audio_empties_the_player(self) -> None:
        instance = object.__new__(ReconstructionTabCoordinator)
        instance._reconstruction_player_logic = MagicMock()

        instance._on_audio_data_changed(None)

        instance._reconstruction_player_logic.clear_audio.assert_called_once_with()
        instance._reconstruction_player_logic.load_audio_data.assert_not_called()


@pytest.fixture
def removal_coordinator() -> ReconstructionTabCoordinator:
    instance = object.__new__(ReconstructionTabCoordinator)
    instance._dialogs = MagicMock()
    instance._browser_logic = MagicMock()
    instance._browser_panel = MagicMock()
    instance._reconstruction_manager = MagicMock()
    instance._language_manager = FakeLanguageManager(TEXTS)
    instance._lbl_remove = "Remove"
    instance._msg_load_error = LOAD_ERROR_KEY
    return instance


class TestRemoveTreeEntries:
    def test_request_remove_reconstruction_prompts_confirmation(
        self,
        removal_coordinator: ReconstructionTabCoordinator,
    ) -> None:
        path = Path("tone.strec")

        removal_coordinator._request_remove_reconstruction(path)

        confirmation = removal_coordinator._dialogs.show_confirmation.call_args.kwargs
        assert confirmation["message"] == REMOVE_RECONSTRUCTION_MESSAGE_KEY
        assert confirmation["path"] == path

        confirmation["on_confirm"]()
        removal_coordinator._browser_logic.remove_path.assert_called_once_with(path)

    def test_removing_open_reconstruction_detaches_and_marks_it_dirty(
        self,
        removal_coordinator: ReconstructionTabCoordinator,
    ) -> None:
        path = Path("tone.strec")
        removal_coordinator._reconstruction_manager.filepath = path

        removal_coordinator._remove_reconstruction(path)

        removal_coordinator._reconstruction_manager.detach_current_reconstruction.assert_called_once_with()
        removal_coordinator._reconstruction_manager.mark_updated.assert_called_once_with()
        removal_coordinator._browser_logic.remove_path.assert_called_once_with(path)
        removal_coordinator._browser_panel.refresh.assert_called_once_with()

    def test_removing_open_directory_detaches_loaded_reconstruction_inside_it(
        self,
        removal_coordinator: ReconstructionTabCoordinator,
    ) -> None:
        directory = Path("set")
        removal_coordinator._reconstruction_manager.filepath = directory / "tone.strec"

        removal_coordinator._remove_directory(directory)

        removal_coordinator._reconstruction_manager.detach_current_reconstruction.assert_called_once_with()
        removal_coordinator._reconstruction_manager.mark_updated.assert_called_once_with()
        removal_coordinator._browser_logic.remove_path.assert_called_once_with(directory)
        removal_coordinator._browser_panel.refresh.assert_called_once_with()

    def test_request_remove_directory_prompts_with_path(
        self,
        removal_coordinator: ReconstructionTabCoordinator,
    ) -> None:
        directory = Path("set")

        removal_coordinator._request_remove_directory(directory)

        confirmation = removal_coordinator._dialogs.show_confirmation.call_args.kwargs
        assert confirmation["message"] == REMOVE_DIRECTORY_MESSAGE_KEY
        assert confirmation["path"] == directory


@pytest.fixture
def export_coordinator() -> ReconstructionTabCoordinator:
    """A coordinator with only the collaborators ``_on_export_result`` touches."""
    instance = object.__new__(ReconstructionTabCoordinator)
    instance._dialogs = MagicMock()
    instance._export_messages = ExportMessages.build(LanguageManager(LANG_EN))
    return instance


def _shown_message(coordinator: ReconstructionTabCoordinator) -> str:
    _, message, _ = coordinator._dialogs.show_message_with_path.call_args.args
    return message


class TestExportResultReportsTruncation:
    def test_a_complete_instrument_export_shows_the_success_message(
        self,
        export_coordinator: ReconstructionTabCoordinator,
    ) -> None:
        export_coordinator._on_export_result(
            ExportSuccess(
                kind=ExportKind.INSTRUMENT,
                filepath=Path("lead.fti"),
                tracker_format=TrackerFormat.FAMITRACKER,
                truncation=None,
            )
        )

        assert _shown_message(export_coordinator) == export_coordinator._export_messages.instrument_success

    def test_a_shortened_instrument_export_names_both_frame_counts(
        self,
        export_coordinator: ReconstructionTabCoordinator,
    ) -> None:
        export_coordinator._on_export_result(
            ExportSuccess(
                kind=ExportKind.INSTRUMENT,
                filepath=Path("lead.fti"),
                tracker_format=TrackerFormat.FAMITRACKER,
                truncation=EnvelopeTruncation(frames=252, source_frames=300, instruments=1),
            )
        )

        message = _shown_message(export_coordinator)
        assert export_coordinator._export_messages.instrument_success in message
        assert "300" in message
        assert "252" in message

    def test_a_shortened_reconstruction_export_counts_the_instruments(
        self,
        export_coordinator: ReconstructionTabCoordinator,
    ) -> None:
        export_coordinator._on_export_result(
            ExportSuccess(
                kind=ExportKind.SAMPLE,
                filepath=Path("instruments"),
                tracker_format=TrackerFormat.FAMITRACKER,
                truncation=EnvelopeTruncation(
                    frames=252,
                    source_frames=410,
                    instruments=3,
                ),
            )
        )

        message = _shown_message(export_coordinator)
        assert export_coordinator._export_messages.instruments_success in message
        assert "3" in message

    def test_a_wav_export_shows_its_own_message(
        self,
        export_coordinator: ReconstructionTabCoordinator,
    ) -> None:
        export_coordinator._on_export_result(
            ExportSuccess(
                kind=ExportKind.WAV,
                filepath=Path("track.wav"),
                tracker_format=None,
                truncation=None,
            )
        )

        assert _shown_message(export_coordinator) == export_coordinator._export_messages.wav_success
