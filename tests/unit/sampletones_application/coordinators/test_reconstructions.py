from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators.tabs.reconstruction import (
    ReconstructionTabCoordinator,
)
from sampletones_shared.exceptions import (
    DeserializationError,
    IncompatibleReconstructionVersionError,
    InvalidMetadataError,
    InvalidReconstructionError,
    InvalidReconstructionValuesError,
    LoadReconstructionError,
    UnhandledReconstructionError,
)


@pytest.fixture
def coordinator() -> ReconstructionTabCoordinator:
    """A coordinator with only the collaborators ``load_reconstruction`` touches, bypassing the
    heavy constructor."""
    instance = object.__new__(ReconstructionTabCoordinator)
    instance._browser_panel = MagicMock()
    instance._reconstruction_manager = MagicMock()
    instance._dialogs = MagicMock()
    instance._msg_file_not_found = "file not found"
    instance._msg_load_error = "load error"
    instance._msg_invalid_metadata = "invalid metadata"
    instance._msg_invalid_values = "invalid values"
    instance._msg_invalid_file = "invalid file"
    instance._msg_deserialization_error = "deserialization error"
    instance._tpl_incompatible_version = "got {} expected {}"
    return instance


class TestLoadReconstructionSurfacesConcreteErrors:
    """Each concrete load failure reaches the user through a populated error dialog, so a bad
    reconstruction file is reported rather than swallowed. The browser unlocks in every case."""

    @pytest.mark.parametrize(
        "error, expected_message",
        [
            (InvalidMetadataError("bad metadata"), "invalid metadata"),
            (InvalidReconstructionValuesError("bad values", ValueError("v")), "invalid values"),
            (InvalidReconstructionError("bad file"), "invalid file"),
            (DeserializationError("bad bytes"), "deserialization error"),
            (LoadReconstructionError("unclassified"), "load error"),
            (OSError("io"), "load error"),
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

        coordinator._dialogs.show_error.assert_called_once_with(error, expected_message)
        coordinator._browser_panel.unlock.assert_called_once_with()

    def test_missing_file_shows_file_not_found_dialog(
        self,
        coordinator: ReconstructionTabCoordinator,
    ) -> None:
        error = FileNotFoundError("gone")
        coordinator._reconstruction_manager.load_reconstruction.side_effect = error
        path = Path("sample.stn")

        coordinator.load_reconstruction(path)

        coordinator._dialogs.show_file_not_found.assert_called_once_with(path, "file not found")
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

        coordinator._dialogs.show_error.assert_called_once_with(error, "load error")
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
    instance._ttl_remove_reconstruction = "Remove reconstruction"
    instance._msg_remove_reconstruction = "Remove this reconstruction?"
    instance._ttl_remove_directory = "Remove directory"
    instance._msg_remove_directory = "Remove this directory and all included reconstructions?"
    instance._lbl_remove = "Remove"
    instance._msg_load_error = "load error"
    return instance


class TestRemoveTreeEntries:
    def test_request_remove_reconstruction_prompts_confirmation(
        self,
        removal_coordinator: ReconstructionTabCoordinator,
    ) -> None:
        path = Path("tone.strec")

        removal_coordinator._request_remove_reconstruction(path)

        confirmation = removal_coordinator._dialogs.show_confirmation.call_args.kwargs
        assert confirmation["message"] == "Remove this reconstruction?"
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
        assert confirmation["message"] == "Remove this directory and all included reconstructions?"
        assert confirmation["path"] == directory
