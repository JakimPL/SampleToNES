from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, FrozenSet, Optional, Tuple

import numpy as np
import pyaudio

from sampletones_application.services.base import ServiceBase
from sampletones_application.services.song_player.constants import (
    PREFETCH_SECONDS,
    STOP_POLL_TIMEOUT,
)
from sampletones_application.services.song_player.protocol import RowSynthesizerProtocol
from sampletones_application.services.song_player.result import (
    SongPlaybackError,
    SongPlaybackStopped,
    SongPlayerResult,
    SongPositionUpdate,
)
from sampletones_core.audio import AudioDeviceManager, clip_audio_inplace
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.song_position import SongPosition
from sampletones_shared.constants.audio import UNITY_GAIN
from sampletones_shared.logger import logger


@dataclass(frozen=True)
class _RenderedRow:
    chunk: np.ndarray
    position: SongPosition


class SongPlayerService(ServiceBase[SongPlayerResult]):
    """Streams a song to the audio device through a render-ahead prefetch buffer.

    A synthesis thread renders rows into a buffer bounded by ``PREFETCH_SECONDS`` of
    look-ahead audio; a writer thread drains that buffer to the device with blocking
    ``stream.write()`` calls that pace playback at the audio clock. Keeping synthesis
    off the writer thread lets the buffer absorb synthesis and scheduling jitter, so the
    device stays fed and playback runs continuously.

    Each row's position is emitted as the writer hands that row to the device, so the
    reported playhead tracks the audio the listener is hearing. The caller receives
    ``SongPositionUpdate`` per row and ``SongPlaybackStopped`` when the song ends.
    """

    def __init__(
        self,
        audio_device_manager: AudioDeviceManager,
        synthesizer: RowSynthesizerProtocol,
        *,
        should_loop: Callable[[], bool],
        master_gain: Callable[[], float],
        priority: int = 0,
    ) -> None:
        super().__init__(priority)
        self._audio_device_manager = audio_device_manager
        self._synthesizer = synthesizer
        self._should_loop = should_loop
        self._master_gain = master_gain
        self._stop_event = threading.Event()
        self._resume_event = threading.Event()
        self._render_thread: Optional[threading.Thread] = None
        self._write_thread: Optional[threading.Thread] = None

        self._buffer: Deque[Optional[_RenderedRow]] = deque()
        self._buffer_condition = threading.Condition()
        self._queued_samples: int = 0
        self._prefetch_samples: int = 0
        self._playback_error: Optional[Exception] = None

    @property
    def alive(self) -> bool:
        return self._write_thread is not None and self._write_thread.is_alive()

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
        self._playback_error = None
        self._prefetch_samples = max(1, round(PREFETCH_SECONDS * self._audio_device_manager.sample_rate))
        self._stop_event.clear()
        self._resume_event.set()
        self._render_thread = threading.Thread(
            target=self._render_loop,
            daemon=True,
            name="SongPlayerRenderWorker",
        )
        self._write_thread = threading.Thread(
            target=self._write_loop,
            daemon=True,
            name="SongPlayerWriteWorker",
        )
        self._render_thread.start()
        self._write_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._resume_event.set()
        self._wake_buffer()
        for thread in (self._render_thread, self._write_thread):
            if thread is not None:
                thread.join(timeout=2.0)

        self._render_thread = None
        self._write_thread = None
        self._clear_buffer()

    def pause(self) -> None:
        self._resume_event.clear()

    def resume(self) -> None:
        self._resume_event.set()

    def seek(self, order_position: int) -> None:
        """Moves the live playhead to another order while playback continues.

        This keeps the synthesiser's state (where ``start`` resets it), so voices sounding at the
        moment of the move carry over to the new order — the playhead jumps while the audio plays on.
        Rows already buffered ahead play out first, so the jump lands within one look-ahead window.
        """
        if not self.alive:
            return

        self._synthesizer.set_position(order_position, 0)

    def relocate(self, order_position: int) -> None:
        """Repoints the playhead at another order while keeping the current row.

        Used to follow a structural order edit (insert/remove/move) so playback stays on the
        frame it was sounding: the row within the frame continues from where it was, and
        voices carry over (the synthesiser keeps its state).
        """
        if not self.alive:
            return

        self._synthesizer.set_position(order_position, self._synthesizer.row_index)

    def _render_loop(self) -> None:
        """Renders rows into the prefetch buffer until the song ends or a stop is requested.

        Wraps synthesis failures into ``_playback_error`` and closes the buffer with an
        end marker so the writer thread reports the terminal result through ``CallbackQueue``,
        keeping every result on the service's single result channel.
        """
        try:
            while not self._stop_event.is_set():
                if self._synthesizer.is_finished and not self._loop_to_start():
                    self._enqueue_end()
                    return

                chunk, position = self._synthesizer.render_row()
                self._enqueue_row(_RenderedRow(chunk=chunk, position=position))
        except Exception as exception:  # pylint: disable=broad-exception-caught
            logger.error_with_traceback(exception, f"{self.class_name}: synthesis error")
            self._playback_error = exception
            self._enqueue_end()

    def _write_loop(self) -> None:
        stream = self._open_stream()
        if stream is None:
            return

        try:
            self._drain_to_stream(stream)
        finally:
            stream.stop_stream()
            stream.close()

    def _open_stream(self) -> Optional[pyaudio.Stream]:
        try:
            sample_rate = self._audio_device_manager.sample_rate
            stream = self._audio_device_manager.open_output_stream(
                sample_rate=sample_rate,
                buffer_size=self._audio_device_manager.buffer_size,
            )
            logger.debug(f"{self.class_name}: audio stream opened at {sample_rate} Hz")
            return stream
        except Exception as exception:  # pylint: disable=broad-exception-caught
            logger.error(f"{self.class_name}: failed to open audio stream: {exception}")
            self._emit(SongPlaybackStopped())
            self._stop_event.set()
            self._wake_buffer()
            return None

    def _drain_to_stream(self, stream: pyaudio.Stream) -> None:
        while not self._stop_event.is_set():
            self._resume_event.wait()
            if self._stop_event.is_set():
                return

            popped, row = self._dequeue()
            if not popped or self._stop_event.is_set():
                return

            if row is None:
                self._emit_terminal()
                return

            self._play_row(stream, row)

    def _play_row(self, stream: pyaudio.Stream, row: _RenderedRow) -> None:
        if len(row.chunk):
            stream.write(self._scale_to_gain(row.chunk).tobytes())

        self._emit(SongPositionUpdate(position=row.position))

    def _scale_to_gain(self, chunk: np.ndarray) -> np.ndarray:
        """Scales one row by the live master gain, clipped to the output stream's range.

        The gain is read per row so a slider change is heard on the next row handed to the
        device rather than after the render-ahead buffer drains. Clipping holds a boost above
        unity within the float stream's [-1, 1] range, so the drive into the clip is the
        audible cost of the boost.
        """
        gain = self._master_gain()
        if gain == UNITY_GAIN:
            return chunk

        scaled = chunk * np.float32(gain)
        return clip_audio_inplace(scaled)

    def _emit_terminal(self) -> None:
        if self._playback_error is not None:
            self._emit(SongPlaybackError(error=self._playback_error))
        else:
            self._emit(SongPlaybackStopped())

    def _enqueue_row(self, row: _RenderedRow) -> None:
        """Appends a rendered row once the buffered look-ahead falls below the target.

        Bounding the buffer by queued audio duration holds a constant real-time cushion
        whatever the row length, so short high-tempo rows stay as well-buffered as long ones
        while the render-ahead latency stays bounded.
        """
        with self._buffer_condition:
            while not self._stop_event.is_set() and self._queued_samples >= self._prefetch_samples:
                self._buffer_condition.wait(timeout=STOP_POLL_TIMEOUT)

            if self._stop_event.is_set():
                return

            self._buffer.append(row)
            self._queued_samples += len(row.chunk)
            self._buffer_condition.notify_all()

    def _enqueue_end(self) -> None:
        with self._buffer_condition:
            if self._stop_event.is_set():
                return

            self._buffer.append(None)
            self._buffer_condition.notify_all()

    def _dequeue(self) -> Tuple[bool, Optional[_RenderedRow]]:
        with self._buffer_condition:
            while not self._stop_event.is_set() and not self._buffer:
                self._buffer_condition.wait(timeout=STOP_POLL_TIMEOUT)

            if not self._buffer:
                return False, None

            row = self._buffer.popleft()
            if row is not None:
                self._queued_samples -= len(row.chunk)
                self._buffer_condition.notify_all()

            return True, row

    def _wake_buffer(self) -> None:
        with self._buffer_condition:
            self._buffer_condition.notify_all()

    def _clear_buffer(self) -> None:
        with self._buffer_condition:
            self._buffer.clear()
            self._queued_samples = 0

    def _loop_to_start(self) -> bool:
        """Wraps the playhead back to the song start when looping is on; reports whether it looped.

        A song with no orders stays finished after the wrap, so looping reports ``False`` there and
        playback stops. Resetting mirrors a fresh ``start`` so the loop replays the song from clean
        channel state.
        """
        if not self._should_loop():
            return False

        self._synthesizer.set_position(0, 0)
        if self._synthesizer.is_finished:
            return False

        self._synthesizer.reset()
        return True
