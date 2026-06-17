from __future__ import annotations

import threading
from typing import FrozenSet, Optional

import pyaudio

from sampletones_application.logic.sequencer.playback.protocol import RowSynthesizerProtocol
from sampletones_application.services.base import ServiceBase
from sampletones_application.services.song_player_result import (
    SongPlaybackError,
    SongPlaybackStopped,
    SongPlayerResult,
    SongPositionUpdate,
)
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.enums import GeneratorName
from sampletones_shared.logger import logger


class SongPlayerService(ServiceBase[SongPlayerResult]):
    """Streams audio from a RowSynthesizer to the audio device on a background thread.

    Blocking ``stream.write()`` provides natural row-rate pacing — no sleep needed.
    The caller receives ``SongPositionUpdate`` after each row and ``SongPlaybackStopped``
    when the song ends or ``stop()`` is called.
    """

    def __init__(
        self,
        audio_device_manager: AudioDeviceManager,
        synthesizer: RowSynthesizerProtocol,
        *,
        priority: int = 0,
    ) -> None:
        super().__init__(priority)
        self._audio_device_manager = audio_device_manager
        self._synthesizer = synthesizer
        self._stop_event = threading.Event()
        self._resume_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._stream: Optional[pyaudio.Stream] = None

    @property
    def alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def is_playing(self) -> bool:
        return self.alive and self._resume_event.is_set()

    @property
    def is_paused(self) -> bool:
        return self.alive and not self._resume_event.is_set()

    def start(
        self,
        *,
        order_position: int = 0,
        row_index: int = 0,
        active_channels: FrozenSet[GeneratorName],
    ) -> None:
        self.stop()
        self._synthesizer.set_position(order_position, row_index)
        self._synthesizer.set_channel_mask(active_channels)
        self._synthesizer.reset()
        self._stop_event.clear()
        self._resume_event.set()
        self._thread = threading.Thread(
            target=self._playback_loop,
            daemon=True,
            name="SongPlayerWorker",
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._resume_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

        self._thread = None

    def pause(self) -> None:
        self._resume_event.clear()

    def resume(self) -> None:
        self._resume_event.set()

    def _playback_loop(self) -> None:
        try:
            sample_rate = self._audio_device_manager.sample_rate
            frame_length = sample_rate // 60
            self._stream = self._audio_device_manager.open_output_stream(
                sample_rate=sample_rate,
                buffer_size=frame_length,
            )
            logger.debug(f"{self.class_name}: audio stream opened at {sample_rate} Hz")
        except Exception as exception:  # pylint: disable=broad-exception-caught
            logger.error(f"{self.class_name}: failed to open audio stream: {exception}")
            self._emit(SongPlaybackStopped())
            return

        try:
            while not self._stop_event.is_set():
                self._resume_event.wait()
                if self._stop_event.is_set():
                    break

                if self._synthesizer.is_finished:
                    self._emit(SongPlaybackStopped())
                    break

                self._render_and_emit_row(self._stream)

                if self._synthesizer.is_finished:
                    self._emit(SongPlaybackStopped())
                    break
        except Exception as exception:  # pylint: disable=broad-exception-caught
            logger.error_with_traceback(
                exception,
                f"{self.class_name}: playback error",
            )
            self._emit(SongPlaybackError(error=exception))
        finally:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

    def _render_and_emit_row(self, stream: pyaudio.Stream) -> None:
        audio_chunk, position_before = self._synthesizer.render_row()
        if len(audio_chunk):
            stream.write(audio_chunk.tobytes())

        self._emit(SongPositionUpdate(position=position_before))
