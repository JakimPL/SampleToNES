from pathlib import Path
from typing import Callable, Optional

from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.exceptions import SampleToNESError
from sampletones_shared.logger import logger
from sampletones_shared.paths import extensions
from sampletones_shared.utils.callbacks import CallbackMixin


class FilePlayback(CallbackMixin):
    """Wherever a file is named and asked to sound, this is what answers.

    A reconstruction is read and its approximation played; an audio file is played from disk. The
    browser's tree, a row in the converter's list and a menu item all name a file the same way, so
    what a suffix means and what a failure to read one reports stand in one place.
    """

    def __init__(self, audio_device_manager: AudioDeviceManager) -> None:
        self._audio_device_manager = audio_device_manager

        self.on_error: Optional[Callable[[Exception], None]] = None

    @staticmethod
    def plays(path: Path) -> bool:
        """Whether this is a file the player knows how to sound."""
        suffix = path.suffix.lower()
        return suffix == extensions.EXT_FILE_RECONSTRUCTION or suffix in extensions.EXT_FILES_AUDIO

    def play(self, path: Path) -> None:
        """Play a file on demand, preempting the auxiliary preview and the players.

        Asking for a file by name is a deliberate action, so it sounds at ``NORMAL`` priority and
        outranks the reconstruction and sequencer players.
        """
        self.play_at(path, PlaybackPriority.NORMAL)

    def play_at(self, path: Path, priority: PlaybackPriority) -> None:
        """Play a file at the priority the gesture asking for it carries."""
        match path.suffix.lower():
            case extensions.EXT_FILE_RECONSTRUCTION:
                self._play_reconstruction(path, priority)
            case suffix if suffix in extensions.EXT_FILES_AUDIO:
                self._audio_device_manager.play_file(path, update=False, priority=priority)

    def _play_reconstruction(self, path: Path, priority: PlaybackPriority) -> None:
        try:
            reconstruction = Reconstruction.load(path)
        except (OSError, SampleToNESError) as exception:
            logger.error_with_traceback(exception, f"Failed to play reconstruction file: {path}")
            self.call(self.on_error, exception)
            return

        self._audio_device_manager.play(reconstruction.approximation, update=False, priority=priority)
