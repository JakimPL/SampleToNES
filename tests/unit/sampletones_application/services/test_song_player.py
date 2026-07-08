from unittest.mock import MagicMock

from sampletones_application.services.song_player.player import SongPlayerService
from sampletones_application.services.song_player.result import (
    SongPlaybackStopped,
    SongPositionUpdate,
)
from sampletones_core.project.song_position import SongPosition


def _make_service(*, is_finished: bool = False, should_loop: bool = False) -> SongPlayerService:
    audio_device_manager = MagicMock()
    synthesizer = MagicMock()
    synthesizer.is_finished = is_finished
    return SongPlayerService(audio_device_manager, synthesizer, should_loop=lambda: should_loop)


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
        service._thread = MagicMock(is_alive=MagicMock(return_value=True))

        service.seek(2)

        service._synthesizer.set_position.assert_called_once_with(2, 0)

    def test_seek_does_not_reset_voices(self) -> None:
        service = _make_service()
        service._thread = MagicMock(is_alive=MagicMock(return_value=True))

        service.seek(2)

        service._synthesizer.reset.assert_not_called()


class TestSongPlayerServiceRelocate:
    def test_relocate_does_nothing_when_not_alive(self) -> None:
        service = _make_service()

        service.relocate(2)

        service._synthesizer.set_position.assert_not_called()

    def test_relocate_keeps_current_row_when_alive(self) -> None:
        service = _make_service()
        service._thread = MagicMock(is_alive=MagicMock(return_value=True))
        service._synthesizer.row_index = 5

        service.relocate(2)

        service._synthesizer.set_position.assert_called_once_with(2, 5)

    def test_relocate_does_not_reset_voices(self) -> None:
        service = _make_service()
        service._thread = MagicMock(is_alive=MagicMock(return_value=True))
        service._synthesizer.row_index = 0

        service.relocate(2)

        service._synthesizer.reset.assert_not_called()


class TestSongPlayerServiceStop:
    def test_stop_sets_stop_event(self) -> None:
        service = _make_service()
        service.stop()
        assert service._stop_event.is_set()

    def test_stop_clears_thread_reference(self) -> None:
        service = _make_service()
        service.stop()
        assert service._thread is None

    def test_stop_is_idempotent_when_already_stopped(self) -> None:
        service = _make_service()
        service.stop()
        service.stop()
        assert service._thread is None


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
        received_a: list = []
        received_b: list = []
        service.subscribe(received_a.append)
        service.subscribe(received_b.append)

        result = SongPlaybackStopped()
        service._emit(result)

        assert received_a == [result]
        assert received_b == [result]


class TestSongPlayerServiceRenderAndEmit:
    def test_render_and_emit_row_emits_position_update(self) -> None:
        import numpy as np

        service = _make_service()
        received = []
        service.subscribe(received.append)

        position = SongPosition(order_position=1, row_index=3)
        service._synthesizer.render_row.return_value = (np.zeros(100, dtype=np.float32), position)

        mock_stream = MagicMock()
        service._render_and_emit_row(mock_stream)

        assert len(received) == 1
        assert isinstance(received[0], SongPositionUpdate)
        assert received[0].position is position

    def test_render_and_emit_row_writes_non_empty_audio(self) -> None:
        import numpy as np

        service = _make_service()
        service.subscribe(lambda result: None)

        audio = np.ones(100, dtype=np.float32)
        position = SongPosition()
        service._synthesizer.render_row.return_value = (audio, position)

        mock_stream = MagicMock()
        service._render_and_emit_row(mock_stream)

        mock_stream.write.assert_called_once_with(audio.tobytes())

    def test_render_and_emit_row_skips_write_for_empty_audio(self) -> None:
        import numpy as np

        service = _make_service()
        service.subscribe(lambda result: None)

        empty_audio = np.zeros(0, dtype=np.float32)
        position = SongPosition()
        service._synthesizer.render_row.return_value = (empty_audio, position)

        mock_stream = MagicMock()
        service._render_and_emit_row(mock_stream)

        mock_stream.write.assert_not_called()
