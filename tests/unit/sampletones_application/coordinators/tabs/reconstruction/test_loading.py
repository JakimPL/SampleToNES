from pathlib import Path
from typing import Dict, Final
from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators.tabs.reconstruction.loading import ReconstructionLoading
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
TEXTS: Final[Dict[str, str]] = {INCOMPATIBLE_VERSION_KEY: "got {} expected {}"}
SAMPLE: Final[Path] = Path("sample.stn")


@pytest.fixture
def manager() -> MagicMock:
    return MagicMock()


@pytest.fixture
def dialogs() -> MagicMock:
    return MagicMock()


@pytest.fixture
def loading(manager: MagicMock, dialogs: MagicMock) -> ReconstructionLoading:
    return ReconstructionLoading(manager, dialogs=dialogs, language_manager=FakeLanguageManager(TEXTS))


class TestLoadReconstructionSurfacesConcreteErrors:
    """Each concrete load failure reaches the user through a populated error dialog, so a bad
    reconstruction file is reported rather than swallowed.
    """

    @pytest.mark.parametrize(
        "error, expected_message",
        [
            (InvalidMetadataError("bad metadata"), INVALID_METADATA_KEY),
            (InvalidReconstructionValuesError("bad values", ValueError("v")), INVALID_VALUES_KEY),
            (InvalidReconstructionError("bad file"), INVALID_FILE_KEY),
            (DeserializationError("bad bytes"), DESERIALIZATION_ERROR_KEY),
            (LoadReconstructionError("unclassified"), LOAD_ERROR_KEY),
            (UnhandledReconstructionError("wrapped"), LOAD_ERROR_KEY),
            (OSError("io"), LOAD_ERROR_KEY),
            (PermissionError("locked"), LOAD_ERROR_KEY),
            (IsADirectoryError("a folder"), LOAD_ERROR_KEY),
        ],
    )
    def test_concrete_error_shows_populated_dialog(
        self,
        loading: ReconstructionLoading,
        manager: MagicMock,
        dialogs: MagicMock,
        error: Exception,
        expected_message: str,
    ) -> None:
        manager.load_reconstruction.side_effect = error

        loading.load(SAMPLE)

        dialogs.show_error.assert_called_once_with(error, expected_message)
        dialogs.show_file_not_found.assert_not_called()

    def test_missing_file_shows_file_not_found_dialog(
        self,
        loading: ReconstructionLoading,
        manager: MagicMock,
        dialogs: MagicMock,
    ) -> None:
        manager.load_reconstruction.side_effect = FileNotFoundError("gone")

        loading.load(SAMPLE)

        dialogs.show_file_not_found.assert_called_once_with(SAMPLE, FILE_NOT_FOUND_KEY)
        dialogs.show_error.assert_not_called()

    def test_incompatible_version_dialog_reports_both_versions(
        self,
        loading: ReconstructionLoading,
        manager: MagicMock,
        dialogs: MagicMock,
    ) -> None:
        error = IncompatibleReconstructionVersionError("mismatch", expected_version="2.0", actual_version="9.0")
        manager.load_reconstruction.side_effect = error

        loading.load(SAMPLE)

        dialogs.show_error.assert_called_once_with(error, "got 9.0 expected 2.0")

    def test_a_loaded_file_shows_no_dialog(
        self,
        loading: ReconstructionLoading,
        manager: MagicMock,
        dialogs: MagicMock,
    ) -> None:
        loading.load(SAMPLE)

        manager.load_reconstruction.assert_called_once_with(SAMPLE)
        assert dialogs.method_calls == []

    def test_unexpected_error_propagates(
        self,
        loading: ReconstructionLoading,
        manager: MagicMock,
        dialogs: MagicMock,
    ) -> None:
        """A failure outside the load contract is a bug, so it reaches the caller unreported."""
        manager.load_reconstruction.side_effect = RuntimeError("bug")

        with pytest.raises(RuntimeError):
            loading.load(SAMPLE)

        dialogs.show_error.assert_not_called()
