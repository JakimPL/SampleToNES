import threading
from typing import Callable, Optional

import numpy as np

from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_core.audio.output import AudioOutput, AudioSource, BufferSource, Playback, PlaybackListener
from sampletones_core.audio.output.source import ReportT
from sampletones_core.constants.audio import START_OF_AUDIO


class PreviewPlayer:
    """The one owner of every preview: a file or a document picked in a browser, a voice of the pool, a key
    auditioned, a key played live.

    Each preview of audio plays at the rate its audio was made at, so it keeps its pitch and length on a
    device of any rate, and the owner asking for it hears its positions and its end through its own
    listener. The latest preview is held here, so the transport's Stop silences whichever preview sounds.
    A key played on a MIDI keyboard asks from the thread its keyboard reports on, so a claim and the stop
    are each decided under a lock, and the preview held is always the latest claim.
    """

    def __init__(self, output: AudioOutput) -> None:
        self._output = output
        self._lock = threading.Lock()
        self._stop: Optional[Callable[[], bool]] = None

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
        source = BufferSource(audio, sample_rate=sample_rate, start=START_OF_AUDIO)
        return self.play_source(source, rank=rank, listener=listener)

    def play_source(
        self,
        source: AudioSource[ReportT],
        *,
        rank: PlaybackPriority,
        listener: PlaybackListener[ReportT],
    ) -> Optional[Playback[ReportT]]:
        """Sounds ``source`` at ``rank``, as the preview Stop reaches from now on.

        Args:
            source: What the preview reads its sound from.
            rank: The rank the preview claims the output at.
            listener: The owner asking for the preview, which hears its positions and its end.

        Returns:
            Optional[Playback[ReportT]]: The preview's playback, or ``None`` where a sound ranked above it holds
                the output.

        Raises:
            NoOutputDeviceError: If no output device is in force.
        """
        with self._lock:
            playback = self._output.play(source, rank=rank, listener=listener)
            if playback is not None:
                self._stop = playback.stop

        return playback

    def stop(self) -> None:
        """Silences the preview sounding, which its owner hears as a stop."""
        with self._lock:
            stop, self._stop = self._stop, None
            if stop is not None:
                stop()
