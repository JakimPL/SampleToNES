from functools import partial
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.logic.shared.preview_player import PreviewPlayer
from sampletones_application.logic.shared.previews import DocumentPreviews
from sampletones_core.audio import read_mono
from sampletones_core.audio.output import Ending, Playback
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.exceptions import PlaybackError, SampleToNESError
from sampletones_shared.logger import logger
from sampletones_shared.paths import extensions
from sampletones_shared.utils.callbacks import CallbackMixin


class FilePlayback(CallbackMixin):
    """Wherever a file is named and asked to sound, this is what answers.

    A reconstruction is read and previewed whole through the document previews, so its sound is
    the render the cache keeps or the one a worker lands a moment later; an audio file is read from
    disk as one channel at the rate it was recorded at. Either sounds through the preview player at
    its own rate. The browser's tree, a row in the converter's list and a menu item all name a file
    the same way, so what a suffix means and what a failure to read one reports stand in one place.
    A file that fails to read, a device that refuses the sound, a document's render that fails and a
    sound that fails as it plays each report through ``on_error``, once.
    """

    def __init__(
        self,
        preview_player: PreviewPlayer,
        previews: DocumentPreviews,
    ) -> None:
        self._preview_player = preview_player
        self._previews = previews
        self._playback: Optional[Playback[int]] = None

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
                self._play_audio(path, priority)

    def positioned(self, _playback: Playback[int], _report: int) -> None:
        """Hears where a file stands, which no browser draws."""
        return None

    def ended(self, playback: Playback[int], ending: Ending) -> None:
        """Reports a failure of the file sounded last."""
        if playback is not self._playback:
            return

        self._playback = None
        if ending.error is not None:
            self.call(self.on_error, ending.error)

    def _play_audio(self, path: Path, priority: PlaybackPriority) -> None:
        try:
            audio, sample_rate = read_mono(path)
        except (OSError, SampleToNESError) as exception:
            logger.error_with_traceback(exception, f"Failed to play audio file: {path}")
            self.call(self.on_error, exception)
            return

        self._sound(audio, sample_rate, priority=priority)

    def _play_reconstruction(self, path: Path, priority: PlaybackPriority) -> None:
        try:
            reconstruction = Reconstruction.load(path)
        except (OSError, SampleToNESError) as exception:
            logger.error_with_traceback(exception, f"Failed to play reconstruction file: {path}")
            self.call(self.on_error, exception)
            return

        self._previews.play(reconstruction, partial(self._sound, priority=priority), self._report)

    def _sound(
        self,
        audio: np.ndarray,
        sample_rate: int,
        *,
        priority: PlaybackPriority,
    ) -> None:
        try:
            playback = self._preview_player.play(audio, sample_rate=sample_rate, rank=priority, listener=self)
        except PlaybackError as exception:
            self.call(self.on_error, exception)
            return

        if playback is not None:
            self._playback = playback

    def _report(self, exception: Exception) -> None:
        self.call(self.on_error, exception)
