from typing import Optional

import numpy as np

from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_core.audio.output import AudioOutput, BufferSource, Playback, PlaybackListener
from sampletones_core.constants.audio import START_OF_AUDIO


class PreviewPlayer:
    """The one owner of every preview: a file or a document picked in a browser, a voice of the pool, a key
    auditioned.

    Each preview plays at the rate its audio was made at, so it keeps its pitch and length on a device of any
    rate, and the owner asking for it hears its positions and its end through its own listener. The latest
    preview is held here, so the transport's Stop silences whichever preview sounds.
    """

    def __init__(self, output: AudioOutput) -> None:
        self._output = output
        self._playback: Optional[Playback[int]] = None

    def play(
        self,
        audio: np.ndarray,
        *,
        sample_rate: int,
        rank: PlaybackPriority,
        listener: PlaybackListener[int],
    ) -> Optional[Playback[int]]:
        """Sounds ``audio`` from its start at ``rank``.

        Args:
            audio: The preview's samples, one channel.
            sample_rate: The rate the audio was made at.
            rank: The rank the preview claims the output at.
            listener: The owner asking for the preview, which hears its positions and its end.

        Returns:
            Optional[Playback[int]]: The preview's playback, or ``None`` where a sound ranked above it holds
                the output.

        Raises:
            NoOutputDeviceError: If no output device is in force.
        """
        playback = self._output.play(
            BufferSource(audio, sample_rate=sample_rate, start=START_OF_AUDIO),
            rank=rank,
            listener=listener,
        )
        if playback is not None:
            self._playback = playback

        return playback

    def stop(self) -> None:
        """Silences the preview sounding, which its owner hears as a stop."""
        playback, self._playback = self._playback, None
        if playback is not None:
            playback.stop()
