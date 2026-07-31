from pathlib import Path

from sampletones_application.categories.elements.reconstructions import (
    ReconstructionPanelElements,
    ReconstructionsBrowserElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.logic.reconstruction.audio_location import resolve_original_audio
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_shared.exceptions import SampleToNESError
from sampletones_shared.logger import logger
from sampletones_shared.utils.system.paths import open_path_in_explorer


class OriginalAudioLocator:
    """Reveals the original audio recorded by a browsed reconstruction, loading the file on demand."""

    def __init__(
        self,
        *,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
    ) -> None:
        self._dialogs = dialogs
        self._msg_load_error = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.BROWSER,
            TextType.MESSAGE,
            ReconstructionsBrowserElements.LOAD_ERROR,
        ]
        self._msg_locate_failed = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.RECONSTRUCTION,
            TextType.MESSAGE,
            ReconstructionPanelElements.LOCATE_AUDIO_FAILED,
        ]

    def locate(self, filepath: Path) -> None:
        """Reads the reconstruction at the path and reveals its recorded original audio.

        A reconstruction that reads back a recorded location has that file revealed in the OS
        file manager. A reconstruction detached from its origin resolves to no location and is
        left as is; a recorded location whose file has since moved surfaces a not-found dialog.
        """
        try:
            audio_filepath = resolve_original_audio(filepath)
        except (SampleToNESError, OSError) as exception:
            logger.error_with_traceback(exception, f"Failed to read reconstruction from {filepath}")
            self._dialogs.show_error(exception, self._msg_load_error)
            return

        if audio_filepath is None:
            return

        if not audio_filepath.exists():
            self._dialogs.show_file_not_found(
                audio_filepath,
                self._msg_locate_failed,
            )
            return

        open_path_in_explorer(audio_filepath)
