from pathlib import Path
from typing import Any, Dict, Final
from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators.tabs.reconstruction.removals import ReconstructionRemovals
from sampletones_application.logic.reconstruction.rewrites.steps import StemRemovalRequest
from tests.suite.language import FakeLanguageManager
from tests.suite.stems import STEM_B_ID

REMOVE_FILE_ERROR_KEY: Final[str] = "reconstructions.browser.message.remove_file_error"
REMOVE_DIRECTORY_ERROR_KEY: Final[str] = "reconstructions.browser.message.remove_directory_error"
REMOVE_RECONSTRUCTION_MESSAGE_KEY: Final[str] = "reconstructions.browser.message.remove_reconstruction_message"
REMOVE_DIRECTORY_MESSAGE_KEY: Final[str] = "reconstructions.browser.message.remove_directory_message"
OPEN_FILE: Final[Path] = Path("tone.strec")
OPEN_FOLDER: Final[Path] = Path("set")


@pytest.fixture
def manager() -> MagicMock:
    return MagicMock()


@pytest.fixture
def browser_logic() -> MagicMock:
    return MagicMock()


@pytest.fixture
def browser_panel() -> MagicMock:
    return MagicMock()


@pytest.fixture
def stems_panel() -> MagicMock:
    return MagicMock()


@pytest.fixture
def dialogs() -> MagicMock:
    return MagicMock()


@pytest.fixture
def requests() -> MagicMock:
    return MagicMock()


@pytest.fixture
def detached() -> MagicMock:
    return MagicMock()


@pytest.fixture
def removals(
    manager: MagicMock,
    browser_logic: MagicMock,
    browser_panel: MagicMock,
    stems_panel: MagicMock,
    dialogs: MagicMock,
    requests: MagicMock,
    detached: MagicMock,
) -> ReconstructionRemovals:
    return ReconstructionRemovals(
        manager,
        browser_logic,
        browser_panel,
        stems_panel,
        dialogs=dialogs,
        language_manager=FakeLanguageManager(),
        on_rewrite_requested=requests,
        on_document_detached=detached,
    )


def _confirmation(dialogs: MagicMock) -> Dict[str, Any]:
    confirmation: Dict[str, Any] = dialogs.show_confirmation.call_args.kwargs
    return confirmation


class TestRemovingARecording:
    """A recording leaves the open document as a step of its own, once the reader confirms it."""

    def test_a_confirmed_removal_asks_for_the_recording_to_leave(
        self,
        removals: ReconstructionRemovals,
        stems_panel: MagicMock,
        dialogs: MagicMock,
        requests: MagicMock,
    ) -> None:
        stems_panel.stems_list.row.return_value.name = "b"

        removals.request_stem(STEM_B_ID)
        requests.assert_not_called()
        _confirmation(dialogs)["on_confirm"]()

        requests.assert_called_once_with(StemRemovalRequest(stem_id=STEM_B_ID, stem_name="b"))

    def test_a_recording_the_list_no_longer_holds_asks_nothing(
        self,
        removals: ReconstructionRemovals,
        stems_panel: MagicMock,
        dialogs: MagicMock,
        requests: MagicMock,
    ) -> None:
        stems_panel.stems_list.row.return_value = None

        removals.request_stem(STEM_B_ID)

        dialogs.show_confirmation.assert_not_called()
        requests.assert_not_called()


class TestRemoveTreeEntries:
    def test_request_remove_reconstruction_prompts_confirmation(
        self,
        removals: ReconstructionRemovals,
        dialogs: MagicMock,
        browser_logic: MagicMock,
    ) -> None:
        removals.request_reconstruction(OPEN_FILE)

        confirmation = _confirmation(dialogs)
        assert confirmation["message"] == REMOVE_RECONSTRUCTION_MESSAGE_KEY
        assert confirmation["path"] == OPEN_FILE
        browser_logic.remove_path.assert_not_called()

        confirmation["on_confirm"]()
        browser_logic.remove_path.assert_called_once_with(OPEN_FILE)

    def test_removing_open_reconstruction_detaches_and_marks_it_dirty(
        self,
        removals: ReconstructionRemovals,
        manager: MagicMock,
        browser_logic: MagicMock,
        browser_panel: MagicMock,
        detached: MagicMock,
    ) -> None:
        """The document stays open as unsaved changes, and is shown without the file it lost."""
        manager.is_backed_by.return_value = True

        removals._remove_reconstruction(OPEN_FILE)

        manager.is_backed_by.assert_called_once_with(OPEN_FILE)
        manager.detach_current_reconstruction.assert_called_once_with()
        manager.mark_updated.assert_called_once_with()
        detached.assert_called_once_with()
        browser_logic.remove_path.assert_called_once_with(OPEN_FILE)
        browser_panel.refresh.assert_called_once_with()

    def test_the_open_document_is_asked_about_before_the_file_goes(
        self,
        removals: ReconstructionRemovals,
        manager: MagicMock,
        browser_logic: MagicMock,
    ) -> None:
        """A file that is gone backs nothing, so whether it backed the document is read first."""
        order = MagicMock()
        order.attach_mock(manager.is_backed_by, "is_backed_by")
        order.attach_mock(browser_logic.remove_path, "remove_path")

        removals._remove_reconstruction(OPEN_FILE)

        steps = [name for name, _args, _kwargs in order.mock_calls if name in ("is_backed_by", "remove_path")]
        assert steps == ["is_backed_by", "remove_path"]

    def test_a_file_that_stays_keeps_the_open_document_on_it(
        self,
        removals: ReconstructionRemovals,
        manager: MagicMock,
        browser_logic: MagicMock,
        browser_panel: MagicMock,
        dialogs: MagicMock,
        detached: MagicMock,
    ) -> None:
        manager.is_backed_by.return_value = True
        browser_logic.remove_path.side_effect = OSError("busy")

        removals._remove_reconstruction(OPEN_FILE)

        manager.detach_current_reconstruction.assert_not_called()
        manager.mark_updated.assert_not_called()
        detached.assert_not_called()
        browser_panel.refresh.assert_not_called()
        assert dialogs.show_error.call_args.args[1] == REMOVE_FILE_ERROR_KEY

    def test_removing_another_file_leaves_the_open_document_as_it_is(
        self,
        removals: ReconstructionRemovals,
        manager: MagicMock,
        browser_logic: MagicMock,
        detached: MagicMock,
    ) -> None:
        manager.is_backed_by.return_value = False

        removals._remove_reconstruction(Path("other.strec"))

        manager.detach_current_reconstruction.assert_not_called()
        detached.assert_not_called()
        browser_logic.remove_path.assert_called_once_with(Path("other.strec"))

    def test_removing_open_directory_detaches_loaded_reconstruction_inside_it(
        self,
        removals: ReconstructionRemovals,
        manager: MagicMock,
        browser_logic: MagicMock,
        browser_panel: MagicMock,
        detached: MagicMock,
    ) -> None:
        manager.lies_within.return_value = True

        removals._remove_directory(OPEN_FOLDER)

        manager.lies_within.assert_called_once_with(OPEN_FOLDER)
        manager.detach_current_reconstruction.assert_called_once_with()
        manager.mark_updated.assert_called_once_with()
        detached.assert_called_once_with()
        browser_logic.remove_path.assert_called_once_with(OPEN_FOLDER)
        browser_panel.refresh.assert_called_once_with()

    def test_removing_another_directory_leaves_the_open_document_as_it_is(
        self,
        removals: ReconstructionRemovals,
        manager: MagicMock,
        browser_logic: MagicMock,
    ) -> None:
        manager.lies_within.return_value = False

        removals._remove_directory(Path("other"))

        manager.detach_current_reconstruction.assert_not_called()
        browser_logic.remove_path.assert_called_once_with(Path("other"))

    def test_a_directory_that_stays_is_reported_as_a_failed_removal(
        self,
        removals: ReconstructionRemovals,
        manager: MagicMock,
        browser_logic: MagicMock,
        dialogs: MagicMock,
        detached: MagicMock,
    ) -> None:
        manager.lies_within.return_value = True
        browser_logic.remove_path.side_effect = OSError("busy")

        removals._remove_directory(OPEN_FOLDER)

        manager.detach_current_reconstruction.assert_not_called()
        detached.assert_not_called()
        assert dialogs.show_error.call_args.args[1] == REMOVE_DIRECTORY_ERROR_KEY

    def test_request_remove_directory_prompts_with_path(
        self,
        removals: ReconstructionRemovals,
        dialogs: MagicMock,
    ) -> None:
        removals.request_directory(OPEN_FOLDER)

        confirmation = _confirmation(dialogs)
        assert confirmation["message"] == REMOVE_DIRECTORY_MESSAGE_KEY
        assert confirmation["path"] == OPEN_FOLDER
