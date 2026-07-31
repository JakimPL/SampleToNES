from unittest.mock import MagicMock

import numpy as np

from sampletones_application.services.song_player.player import SongPlayerService, _RenderedRow
from sampletones_application.services.song_player.result import (
    SongPlaybackStopped,
    SongPositionUpdate,
)
from sampletones_core.project.song_position import SongPosition


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
