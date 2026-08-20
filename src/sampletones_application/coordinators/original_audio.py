from pathlib import Path

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.logic.reconstruction.audio_location import resolve_original_audio
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_shared.exceptions import SampleToNESError
from sampletones_shared.logger import logger
from sampletones_shared.utils.system.paths import first_missing, to_paths
from sampletones_shared.utils.system.reveal.selection import open_paths_in_explorer


class OriginalAudioLocator:
    """Reveals the original audio recorded by a browsed reconstruction, loading the file on demand."""

    def __init__(
        self,
        *,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
    ) -> None:
        self._language_manager = language_manager
        self._dialogs = dialogs

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
            self._dialogs.show_error(exception, self._language_manager["reconstructions.browser.message.load_error"])
            return

        audio_paths = to_paths(audio_filepath)
        if not audio_paths:
            return

        missing_path = first_missing(audio_paths)
        if missing_path is not None:
            self._dialogs.show_file_not_found(
                missing_path,
                self._language_manager["reconstructions.reconstruction.message.locate_audio_failed"],
            )
            return

        open_paths_in_explorer(audio_paths)
