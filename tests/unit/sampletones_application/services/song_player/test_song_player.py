import threading
from typing import Callable, Final, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import numpy as np

from sampletones_application.services.song_player.player import (
    SongPlayerService,
    _RenderedRow,
)
from sampletones_application.services.song_player.result import (
    SongPlaybackError,
    SongPlaybackStopped,
    SongPlayerResult,
    SongPositionUpdate,
)
from sampletones_core.project.song_position import SongPosition

SAMPLE_RATE: Final[int] = 44100
WRITE_BLOCK: Final[int] = 64
WAIT_TIMEOUT: Final[float] = 5.0
SHORT_JOIN_TIMEOUT: Final[float] = 0.05
WRITE_RELEASE_DELAY: Final[float] = 0.05
JOIN_TIMEOUT_TARGET: Final[str] = "sampletones_application.services.song_player.player.STOP_JOIN_TIMEOUT"


def _make_service(
    *,
    is_finished: bool = False,
    should_loop: bool = False,
    master_gain: float = 1.0,
) -> SongPlayerService:
    audio_device_manager = MagicMock()
    synthesizer = MagicMock()
    synthesizer.is_finished = is_finished
    return SongPlayerService(
        audio_device_manager,
        synthesizer,
        should_loop=lambda: should_loop,
        master_gain=lambda: master_gain,
    )


class _FakeStream:
    """A stand-in for the device stream that records the frame count of every block handed to it."""

    def __init__(
        self,
        *,
        gate: Optional[threading.Event] = None,
        error: Optional[Exception] = None,
        after_write: Optional[Callable[[], None]] = None,
    ) -> None:
        self._gate = gate
        self._error = error
        self._after_write = after_write
        self.writes: List[int] = []
        self.entered_write = threading.Event()
        self.stopped = threading.Event()
        self.closed = threading.Event()

    def write(self, data: bytes) -> None:
        self.writes.append(len(data) // np.dtype(np.float32).itemsize)
        self.entered_write.set()
        if self._gate is not None:
            self._gate.wait(timeout=WAIT_TIMEOUT)

        if self._after_write is not None:
            self._after_write()

        if self._error is not None:
            raise self._error

    def stop_stream(self) -> None:
        self.stopped.set()

    def close(self) -> None:
        self.closed.set()


class _FakeSynthesizer:
    """Renders a fixed number of equal-length rows and then reports itself finished."""

    def __init__(self, *, rows: int, frames: int) -> None:
        self._rows = rows
        self._frames = frames
        self._rendered = 0
        self.order_position = 0
        self.row_index = 0

    @property
    def is_finished(self) -> bool:
        return self._rendered >= self._rows

    def set_position(self, order_position: int, row_index: int) -> None:
        self.order_position = order_position
        self.row_index = row_index

    def reset(self) -> None:
        self._rendered = 0

    def render_row(self) -> Tuple[np.ndarray, SongPosition]:
        position = SongPosition(order_position=0, row_index=self._rendered)
        self._rendered += 1
        return np.ones(self._frames, dtype=np.float32), position


def _make_device_manager(stream: Optional[_FakeStream] = None) -> MagicMock:
    audio_device_manager = MagicMock()
    audio_device_manager.sample_rate = SAMPLE_RATE
    audio_device_manager.buffer_size = WRITE_BLOCK
    audio_device_manager.open_output_stream.return_value = stream
    return audio_device_manager


def _make_streaming_service(
    audio_device_manager: MagicMock,
    *,
    rows: int = 1,
    frames: int = 4 * WRITE_BLOCK,
) -> SongPlayerService:
    return SongPlayerService(
        audio_device_manager,
        _FakeSynthesizer(rows=rows, frames=frames),
        should_loop=lambda: False,
        master_gain=lambda: 1.0,
    )


def _wedged_thread(gate: threading.Event) -> threading.Thread:
    """A started worker that stays alive until ``gate`` is set."""
    thread = threading.Thread(
        target=lambda: gate.wait(timeout=WAIT_TIMEOUT),
        daemon=True,
        name="WedgedWorker",
    )
    thread.start()
    return thread


class TestSongPlayerServiceInitialState:
    def test_alive_is_false_initially(self) -> None:
        service = _make_service()
        assert service.alive is False

    def test_is_playing_is_false_initially(self) -> None:
        service = _make_service()
        assert service.is_playing is False

    def test_is_paused_is_false_initially(self) -> None:
        service = _make_service()
        assert service.is_paused is False


class TestSongPlayerServicePauseResume:
    def test_pause_clears_resume_event(self) -> None:
        service = _make_service()
        service._resume_event.set()
        service.pause()
        assert not service._resume_event.is_set()

    def test_resume_sets_resume_event(self) -> None:
        service = _make_service()
        service._resume_event.clear()
        service.resume()
        assert service._resume_event.is_set()


class TestSongPlayerServiceSeek:
    def test_seek_does_nothing_when_not_alive(self) -> None:
        service = _make_service()

        service.seek(2)

        service._synthesizer.set_position.assert_not_called()

    def test_seek_sets_synthesizer_position_when_alive(self) -> None:
        service = _make_service()
        service._write_thread = MagicMock(is_alive=MagicMock(return_value=True))

        service.seek(2)

        service._synthesizer.set_position.assert_called_once_with(2, 0)

    def test_seek_does_not_reset_voices(self) -> None:
        service = _make_service()
        service._write_thread = MagicMock(is_alive=MagicMock(return_value=True))

        service.seek(2)

        service._synthesizer.reset.assert_not_called()


class TestSongPlayerServiceRelocate:
    def test_relocate_does_nothing_when_not_alive(self) -> None:
        service = _make_service()

        service.relocate(2)

        service._synthesizer.set_position.assert_not_called()

    def test_relocate_keeps_current_row_when_alive(self) -> None:
        service = _make_service()
        service._write_thread = MagicMock(is_alive=MagicMock(return_value=True))
        service._synthesizer.row_index = 5

        service.relocate(2)

        service._synthesizer.set_position.assert_called_once_with(2, 5)

    def test_relocate_does_not_reset_voices(self) -> None:
        service = _make_service()
        service._write_thread = MagicMock(is_alive=MagicMock(return_value=True))
        service._synthesizer.row_index = 0

        service.relocate(2)

        service._synthesizer.reset.assert_not_called()


class TestSongPlayerServiceStop:
    def test_stop_sets_stop_event(self) -> None:
        service = _make_service()
        service.stop()
        assert service._stop_event.is_set()

    def test_stop_clears_thread_references(self) -> None:
        service = _make_service()
        service.stop()
        assert service._render_thread is None
        assert service._write_thread is None

    def test_stop_is_idempotent_when_already_stopped(self) -> None:
        service = _make_service()
        service.stop()
        service.stop()
        assert service._render_thread is None
        assert service._write_thread is None


class TestSongPlayerServiceLoop:
    def test_loop_to_start_wraps_when_enabled(self) -> None:
        service = _make_service(should_loop=True)
        service._synthesizer.is_finished = False

        looped = service._loop_to_start()

        assert looped is True
        service._synthesizer.set_position.assert_called_once_with(0, 0)
        service._synthesizer.reset.assert_called_once()

    def test_loop_to_start_does_nothing_when_disabled(self) -> None:
        service = _make_service(should_loop=False)

        looped = service._loop_to_start()

        assert looped is False
        service._synthesizer.set_position.assert_not_called()
        service._synthesizer.reset.assert_not_called()

    def test_loop_to_start_stops_on_empty_song(self) -> None:
        service = _make_service(should_loop=True, is_finished=True)

        looped = service._loop_to_start()

        assert looped is False
        service._synthesizer.reset.assert_not_called()


class TestSongPlayerServiceSubscribeAndEmit:
    def test_subscribe_receives_emitted_results(self) -> None:
        service = _make_service()
        received = []
        service.subscribe(received.append)

        result = SongPlaybackStopped()
        service._emit(result)

        assert received == [result]

    def test_multiple_subscribers_all_receive_result(self) -> None:
        service = _make_service()
        received_a = []
        received_b = []
        service.subscribe(received_a.append)
        service.subscribe(received_b.append)

        result = SongPlaybackStopped()
        service._emit(result)

        assert received_a == [result]
        assert received_b == [result]


class TestSongPlayerServicePlayRow:
    def test_play_row_emits_position_update(self) -> None:
        service = _make_service()
        received = []
        service.subscribe(received.append)

        position = SongPosition(order_position=1, row_index=3)
        row = _RenderedRow(chunk=np.zeros(100, dtype=np.float32), position=position)

        mock_stream = MagicMock()
        service._play_row(mock_stream, row)

        assert len(received) == 1
        assert isinstance(received[0], SongPositionUpdate)
        assert received[0].position is position

    def test_play_row_writes_non_empty_audio(self) -> None:
        service = _make_service()
        service.subscribe(lambda result: None)

        audio = np.ones(100, dtype=np.float32)
        row = _RenderedRow(chunk=audio, position=SongPosition())

        mock_stream = MagicMock()
        service._play_row(mock_stream, row)

        mock_stream.write.assert_called_once_with(audio.tobytes())

    def test_play_row_skips_write_for_empty_audio(self) -> None:
        service = _make_service()
        service.subscribe(lambda result: None)

        row = _RenderedRow(chunk=np.zeros(0, dtype=np.float32), position=SongPosition())

        mock_stream = MagicMock()
        service._play_row(mock_stream, row)

        mock_stream.write.assert_not_called()


class TestSongPlayerServiceMasterGain:
    def test_unity_gain_leaves_samples_unchanged(self) -> None:
        service = _make_service(master_gain=1.0)

        chunk = np.array([-0.5, 0.25, 0.75], dtype=np.float32)
        scaled = service._scale_to_gain(chunk)

        assert scaled is chunk

    def test_gain_scales_samples_below_the_clip(self) -> None:
        service = _make_service(master_gain=2.0)

        chunk = np.array([-0.25, 0.1, 0.4], dtype=np.float32)
        scaled = service._scale_to_gain(chunk)

        assert scaled.dtype == np.float32
        np.testing.assert_allclose(scaled, [-0.5, 0.2, 0.8], rtol=1e-6)

    def test_gain_clips_boosted_samples_to_range(self) -> None:
        service = _make_service(master_gain=2.0)

        chunk = np.array([-0.9, 0.6, 1.0], dtype=np.float32)
        scaled = service._scale_to_gain(chunk)

        np.testing.assert_allclose(scaled, [-1.0, 1.0, 1.0], rtol=1e-6)

    def test_gain_is_read_per_row(self) -> None:
        gain = {"value": 1.0}
        audio_device_manager = MagicMock()
        synthesizer = MagicMock()
        service = SongPlayerService(
            audio_device_manager,
            synthesizer,
            should_loop=lambda: False,
            master_gain=lambda: gain["value"],
        )

        chunk = np.array([0.5], dtype=np.float32)
        assert service._scale_to_gain(chunk) is chunk

        gain["value"] = 2.0
        np.testing.assert_allclose(service._scale_to_gain(chunk), [1.0], rtol=1e-6)


class TestSongPlayerServicePrefetch:
    def test_render_loop_ends_when_finished_without_loop(self) -> None:
        service = _make_service(is_finished=True, should_loop=False)

        service._render_loop()

        assert list(service._buffer) == [None]
        service._synthesizer.render_row.assert_not_called()

    def test_drain_writes_buffered_rows_then_reports_stopped(self) -> None:
        service = _make_service()
        received = []
        service.subscribe(received.append)
        service._resume_event.set()

        position = SongPosition(order_position=2, row_index=1)
        service._buffer.append(_RenderedRow(chunk=np.ones(10, dtype=np.float32), position=position))
        service._buffer.append(None)

        mock_stream = MagicMock()
        service._drain_to_stream(mock_stream)

        mock_stream.write.assert_called_once()
        assert isinstance(received[0], SongPositionUpdate)
        assert received[0].position is position
        assert isinstance(received[-1], SongPlaybackStopped)

    def test_drain_returns_without_terminal_when_stopping(self) -> None:
        service = _make_service()
        received = []
        service.subscribe(received.append)
        service._resume_event.set()
        service._stop_event.set()
        service._buffer.append(_RenderedRow(chunk=np.ones(10, dtype=np.float32), position=SongPosition()))

        mock_stream = MagicMock()
        service._drain_to_stream(mock_stream)

        mock_stream.write.assert_not_called()
        assert received == []

    def test_enqueue_row_tracks_queued_samples(self) -> None:
        service = _make_service()
        service._prefetch_samples = 100

        service._enqueue_row(_RenderedRow(chunk=np.zeros(30, dtype=np.float32), position=SongPosition()))

        assert service._queued_samples == 30
        assert len(service._buffer) == 1

    def test_dequeue_releases_queued_samples(self) -> None:
        service = _make_service()
        service._prefetch_samples = 100
        service._enqueue_row(_RenderedRow(chunk=np.zeros(30, dtype=np.float32), position=SongPosition()))

        popped, row = service._dequeue()

        assert popped is True
        assert row is not None
        assert service._queued_samples == 0

    def test_dequeue_returns_no_row_after_stop(self) -> None:
        service = _make_service()
        service._stop_event.set()

        assert service._dequeue() == (False, None)


class TestSongPlayerServiceBoundedWrites:
    def test_start_takes_the_write_block_from_the_device(self) -> None:
        service = _make_streaming_service(_make_device_manager(_FakeStream()))

        service.start()
        service.stop()

        assert service._write_block_frames == WRITE_BLOCK

    def test_row_reaches_the_device_in_buffer_sized_blocks(self) -> None:
        service = _make_service()
        service.subscribe(lambda result: None)
        service._write_block_frames = WRITE_BLOCK

        stream = _FakeStream()
        row = _RenderedRow(chunk=np.ones(3 * WRITE_BLOCK + 8, dtype=np.float32), position=SongPosition())
        service._play_row(stream, row)

        assert stream.writes == [WRITE_BLOCK, WRITE_BLOCK, WRITE_BLOCK, 8]

    def test_stop_mid_row_leaves_the_remaining_blocks_unwritten(self) -> None:
        service = _make_service()
        received: List[SongPlayerResult] = []
        service.subscribe(received.append)
        service._write_block_frames = WRITE_BLOCK

        stream = _FakeStream(after_write=service._stop_event.set)
        row = _RenderedRow(chunk=np.ones(4 * WRITE_BLOCK, dtype=np.float32), position=SongPosition())
        service._play_row(stream, row)

        assert stream.writes == [WRITE_BLOCK]
        assert received == []


class TestSongPlayerServiceStopQuiescence:
    def test_stop_returns_after_the_writer_closed_its_stream(self) -> None:
        gate = threading.Event()
        stream = _FakeStream(gate=gate)
        service = _make_streaming_service(_make_device_manager(stream), rows=8)
        service.subscribe(lambda result: None)

        service.start()
        assert stream.entered_write.wait(timeout=WAIT_TIMEOUT)

        releaser = threading.Timer(WRITE_RELEASE_DELAY, gate.set)
        releaser.start()
        try:
            service.stop()
        finally:
            releaser.cancel()
            gate.set()

        assert service.alive is False
        assert stream.stopped.is_set()
        assert stream.closed.is_set()

    def test_stop_keeps_a_worker_that_outlives_the_deadline(self) -> None:
        gate = threading.Event()
        service = _make_service()
        service._write_thread = _wedged_thread(gate)

        try:
            with patch(JOIN_TIMEOUT_TARGET, SHORT_JOIN_TIMEOUT):
                service.stop()

            assert service._write_thread is not None
            assert service.alive is True
        finally:
            gate.set()

    def test_start_is_refused_while_a_worker_still_holds_the_output(self) -> None:
        gate = threading.Event()
        audio_device_manager = _make_device_manager(_FakeStream())
        service = _make_streaming_service(audio_device_manager)
        service._write_thread = _wedged_thread(gate)

        try:
            with patch(JOIN_TIMEOUT_TARGET, SHORT_JOIN_TIMEOUT):
                service.start()

            audio_device_manager.open_output_stream.assert_not_called()
        finally:
            gate.set()


class TestSongPlayerServiceWriteFailure:
    def test_a_failing_write_reports_a_playback_error(self) -> None:
        error = OSError("device disappeared")
        service = _make_streaming_service(_make_device_manager(_FakeStream(error=error)))
        received: List[SongPlayerResult] = []
        service.subscribe(received.append)
        service._resume_event.set()
        service._buffer.append(_RenderedRow(chunk=np.ones(WRITE_BLOCK, dtype=np.float32), position=SongPosition()))

        service._write_loop()

        assert received == [SongPlaybackError(error=error)]

    def test_a_failing_write_still_closes_the_stream(self) -> None:
        stream = _FakeStream(error=OSError("device disappeared"))
        service = _make_streaming_service(_make_device_manager(stream))
        service.subscribe(lambda result: None)
        service._resume_event.set()
        service._buffer.append(_RenderedRow(chunk=np.ones(WRITE_BLOCK, dtype=np.float32), position=SongPosition()))

        service._write_loop()

        assert stream.stopped.is_set()
        assert stream.closed.is_set()
