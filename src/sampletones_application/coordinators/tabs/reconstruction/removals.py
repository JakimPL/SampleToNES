from pathlib import Path
from typing import Callable

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.logic.reconstruction.browser.logic import BrowserLogic
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.logic.reconstruction.rewrites.steps import Rewrite, StemRemovalRequest
from sampletones_application.tags.reconstructions import (
    TAG_RECONSTRUCTIONS_BROWSER_DIALOG_REMOVE_DIRECTORY_CONFIRMATION,
    TAG_RECONSTRUCTIONS_BROWSER_DIALOG_REMOVE_RECONSTRUCTION_CONFIRMATION,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_DIALOG_REMOVE_STEM_CONFIRMATION,
)
from sampletones_application.ui.panels.reconstruction.browser import GUIReconstructionsBrowserPanel
from sampletones_application.ui.panels.reconstruction.stems import GUIReconstructionStemsPanel
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback


class ReconstructionRemovals:
    """What the tab removes once the reader confirms it: a file or a folder of the browser, and a recording
    of the open document.

    A removed file the open document stood on leaves the document open as unsaved changes with no file
    of its own, so a save can still keep them.
    """

    def __init__(
        self,
        reconstruction_manager: ReconstructionManager,
        browser_logic: BrowserLogic,
        browser_panel: GUIReconstructionsBrowserPanel,
        stems_panel: GUIReconstructionStemsPanel,
        *,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
        on_rewrite_requested: Callable[[Rewrite], None],
        on_document_detached: VoidCallback,
    ) -> None:
        self._reconstruction_manager = reconstruction_manager
        self._browser_logic = browser_logic
        self._browser_panel = browser_panel
        self._stems_panel = stems_panel
        self._dialogs = dialogs
        self._language_manager = language_manager
        self._on_rewrite_requested = on_rewrite_requested
        self._on_document_detached = on_document_detached
        self._lbl_remove = language_manager["global.dialog.label.remove"]
        self._msg_remove_file_error = language_manager["reconstructions.browser.message.remove_file_error"]
        self._msg_remove_directory_error = language_manager["reconstructions.browser.message.remove_directory_error"]

    def request_reconstruction(self, filepath: Path) -> None:
        self._dialogs.show_confirmation(
            tag=TAG_RECONSTRUCTIONS_BROWSER_DIALOG_REMOVE_RECONSTRUCTION_CONFIRMATION,
            title=self._language_manager["reconstructions.browser.title.remove_reconstruction_dialog"],
            message=self._language_manager["reconstructions.browser.message.remove_reconstruction_message"],
            on_confirm=lambda: self._remove_reconstruction(filepath),
            ok_label=self._lbl_remove,
            path=filepath,
        )

    def request_directory(self, directory: Path) -> None:
        self._dialogs.show_confirmation(
            tag=TAG_RECONSTRUCTIONS_BROWSER_DIALOG_REMOVE_DIRECTORY_CONFIRMATION,
            title=self._language_manager["reconstructions.browser.title.remove_directory_dialog"],
            message=self._language_manager["reconstructions.browser.message.remove_directory_message"],
            on_confirm=lambda: self._remove_directory(directory),
            ok_label=self._lbl_remove,
            path=directory,
        )

    def request_stem(self, stem_id: int) -> None:
        """Asks before a recording leaves the loaded reconstruction, naming the file it stands as."""
        row = self._stems_panel.stems_list.row(str(stem_id))
        if row is None:
            return

        self._dialogs.show_confirmation(
            tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_DIALOG_REMOVE_STEM_CONFIRMATION,
            title=self._language_manager["reconstructions.reconstruction.title.remove_stem_dialog"],
            message=self._language_manager["reconstructions.reconstruction.message.remove_stem_message"],
            on_confirm=lambda: self._on_rewrite_requested(StemRemovalRequest(stem_id=stem_id, stem_name=row.name)),
            ok_label=self._lbl_remove,
            path=row.path,
        )

    def _remove_reconstruction(self, filepath: Path) -> None:
        """Deletes a reconstruction file, keeping the open document once the file it stood on is gone."""
        stood_on_it = self._reconstruction_manager.is_taken_by_removing(filepath)
        try:
            self._browser_logic.remove_path(filepath)
        except OSError as exception:
            logger.error_with_traceback(exception, f"Failed to remove reconstruction: {filepath}")
            self._dialogs.show_error(exception, self._msg_remove_file_error)
            return

        if stood_on_it:
            self._let_go_of_removed_file()

        self._browser_panel.refresh()

    def _remove_directory(self, directory: Path) -> None:
        """Deletes a folder, keeping the open document once the file it stood on inside it is gone."""
        stood_in_it = self._reconstruction_manager.is_taken_by_removing(directory)
        try:
            self._browser_logic.remove_path(directory)
        except OSError as exception:
            logger.error_with_traceback(exception, f"Failed to remove directory: {directory}")
            self._dialogs.show_error(exception, self._msg_remove_directory_error)
            return

        if stood_in_it:
            self._let_go_of_removed_file()

        self._browser_panel.refresh()

    def _let_go_of_removed_file(self) -> None:
        """Holds the open document as unsaved changes with no file of its own, and shows it that way.

        The reader still has the document in front of them, so its changes stay open for a save to
        another file, and the Source card stops naming the file that is gone.
        """
        self._reconstruction_manager.detach_current_reconstruction()
        self._reconstruction_manager.mark_updated()
        self._on_document_detached()
