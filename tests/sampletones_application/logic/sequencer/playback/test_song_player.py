from unittest.mock import MagicMock

from sampletones_application.logic.sequencer.playback.song_player import SongPlayerLogic
from sampletones_application.services.song_player.result import (
    SongPlaybackError,
    SongPlaybackStopped,
    SongPositionUpdate,
)
from sampletones_application.view_model.sequencer.song_player import SongPlayerViewModel
from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.song_position import SongPosition
from tests.sampletones_application.logic.sequencer.playback.conftest import make_controller


def _make_logic(*, is_open: bool = True) -> SongPlayerLogic:
    controller = make_controller()
    if is_open:
        controller._project_manager.new()

    logic = SongPlayerLogic(MagicMock(), controller, Config(), MagicMock(follow_playback=True))
    logic._service = MagicMock(is_playing=False, is_paused=False)
    return logic


def _capture_views(logic: SongPlayerLogic) -> list[SongPlayerViewModel]:
    views: list[SongPlayerViewModel] = []
    logic.on_view_changed = views.append
    return views


class TestPlay:
    def test_play_does_nothing_when_project_not_open(self) -> None:
        logic = _make_logic(is_open=False)
        views = _capture_views(logic)

        logic.play()

        assert not views
        logic._service.start.assert_not_called()

    def test_play_starts_service_from_beginning(self) -> None:
        logic = _make_logic(is_open=True)
        _capture_views(logic)

        logic.play()

        logic._service.start.assert_called_once_with(
            order_position=0,
            row_index=0,
            active_channels=logic._active_channels,
        )

    def test_play_clears_previous_error_in_emitted_view(self) -> None:
        logic = _make_logic(is_open=True)
        logic._last_error = "prior error"
        views = _capture_views(logic)

        logic.play()

        assert views[-1].error is None

    def test_play_emits_view(self) -> None:
        logic = _make_logic(is_open=True)
        views = _capture_views(logic)

        logic.play()

        assert len(views) == 1


class TestPlayFrom:
    def test_play_from_starts_service_at_specified_position(self) -> None:
        logic = _make_logic(is_open=True)
        _capture_views(logic)

        logic.play_from(order_position=2, row_index=4)

        logic._service.start.assert_called_once_with(
            order_position=2,
            row_index=4,
            active_channels=logic._active_channels,
        )

    def test_play_from_stores_specified_position(self) -> None:
        logic = _make_logic(is_open=True)
        _capture_views(logic)

        logic.play_from(order_position=2, row_index=4)

        assert logic._position.order_position == 2
        assert logic._position.row_index == 4

    def test_play_from_does_nothing_when_project_not_open(self) -> None:
        logic = _make_logic(is_open=False)
        views = _capture_views(logic)

        logic.play_from(order_position=1, row_index=0)

        assert not views
        logic._service.start.assert_not_called()

    def test_play_from_emits_view(self) -> None:
        logic = _make_logic(is_open=True)
        views = _capture_views(logic)

        logic.play_from(order_position=1, row_index=2)

        assert len(views) == 1


class TestStop:
    def test_stop_resets_position_to_beginning(self) -> None:
        logic = _make_logic(is_open=True)
        logic._position = SongPosition(order_position=5, row_index=3)
        _capture_views(logic)

        logic.stop()

        assert logic._position.order_position == 0
        assert logic._position.row_index == 0

    def test_stop_emits_view_with_reset_position(self) -> None:
        logic = _make_logic(is_open=True)
        logic._position = SongPosition(order_position=2, row_index=7)
        views = _capture_views(logic)

        logic.stop()

        assert len(views) == 1
        assert views[0].order_position == 0
        assert views[0].row_index == 0


class TestPauseOrResume:
    def test_resumes_when_paused(self) -> None:
        logic = _make_logic(is_open=True)
        logic._service.is_paused = True
        _capture_views(logic)

        logic.pause_or_resume()

        logic._service.resume.assert_called_once()
        logic._service.pause.assert_not_called()

    def test_pauses_when_playing(self) -> None:
        logic = _make_logic(is_open=True)
        logic._service.is_paused = False
        logic._service.is_playing = True
        _capture_views(logic)

        logic.pause_or_resume()

        logic._service.pause.assert_called_once()
        logic._service.resume.assert_not_called()

    def test_starts_play_when_idle_and_loaded(self) -> None:
        logic = _make_logic(is_open=True)
        logic._service.is_paused = False
        logic._service.is_playing = False
        _capture_views(logic)

        logic.pause_or_resume()

        logic._service.start.assert_called_once()

    def test_emits_view_regardless_of_transition(self) -> None:
        logic = _make_logic(is_open=True)
        logic._service.is_paused = True
        views = _capture_views(logic)

        logic.pause_or_resume()

        assert len(views) == 1


class TestOnServiceResult:
    def test_position_update_sets_internal_position(self) -> None:
        logic = _make_logic()
        logic.on_view_changed = lambda _: None

        logic._on_service_result(SongPositionUpdate(position=SongPosition(order_position=3, row_index=5)))

        assert logic._position.order_position == 3
        assert logic._position.row_index == 5

    def test_position_update_fires_on_position_changed(self) -> None:
        logic = _make_logic()
        logic.on_view_changed = lambda _: None
        received: list[tuple[int, int]] = []
        logic.on_position_changed = lambda order, row: received.append((order, row))

        logic._on_service_result(SongPositionUpdate(position=SongPosition(order_position=2, row_index=6)))

        assert received == [(2, 6)]

    def test_position_update_emits_view_with_current_position(self) -> None:
        logic = _make_logic()
        logic.on_position_changed = lambda _order, _row: None
        views = _capture_views(logic)

        logic._on_service_result(SongPositionUpdate(position=SongPosition(order_position=1, row_index=4)))

        assert views[-1].order_position == 1
        assert views[-1].row_index == 4

    def test_playback_stopped_emits_view(self) -> None:
        logic = _make_logic()
        views = _capture_views(logic)

        logic._on_service_result(SongPlaybackStopped())

        assert len(views) == 1

    def test_playback_stopped_emits_idle_view_even_when_worker_still_reports_playing(self) -> None:
        """The worker thread may still be closing its stream when the stop result is processed;
        the emitted view must report idle regardless so the playhead highlight clears."""
        logic = _make_logic()
        logic._service.is_playing = True
        logic._service.is_paused = True
        views = _capture_views(logic)

        logic._on_service_result(SongPlaybackStopped())

        assert views[-1].is_playing is False
        assert views[-1].is_paused is False

    def test_playback_stopped_resets_position_to_beginning(self) -> None:
        logic = _make_logic()
        logic._position = SongPosition(order_position=3, row_index=9)
        views = _capture_views(logic)

        logic._on_service_result(SongPlaybackStopped())

        assert logic._position.order_position == 0
        assert logic._position.row_index == 0
        assert views[-1].order_position == 0
        assert views[-1].row_index == 0

    def test_playback_error_stores_message_in_emitted_view(self) -> None:
        logic = _make_logic()
        logic.on_error = lambda _: None
        views = _capture_views(logic)

        logic._on_service_result(SongPlaybackError(error=ValueError("stream closed")))

        assert views[-1].error == "stream closed"

    def test_playback_error_uses_class_name_when_message_is_empty(self) -> None:
        logic = _make_logic()
        logic.on_error = lambda _: None
        logic.on_view_changed = lambda _: None

        class SilentError(Exception):
            pass

        logic._on_service_result(SongPlaybackError(error=SilentError()))

        assert logic._last_error == "SilentError"

    def test_playback_error_resets_position_to_beginning(self) -> None:
        logic = _make_logic()
        logic.on_error = lambda _: None
        logic.on_view_changed = lambda _: None
        logic._position = SongPosition(order_position=3, row_index=2)

        logic._on_service_result(SongPlaybackError(error=RuntimeError("fail")))

        assert logic._position.order_position == 0
        assert logic._position.row_index == 0

    def test_playback_error_fires_on_error_callback(self) -> None:
        logic = _make_logic()
        logic.on_view_changed = lambda _: None
        errors: list[Exception] = []
        logic.on_error = errors.append

        error = RuntimeError("device lost")
        logic._on_service_result(SongPlaybackError(error=error))

        assert errors == [error]


class TestActiveChannels:
    def test_set_active_channels_is_used_on_next_start(self) -> None:
        logic = _make_logic(is_open=True)
        _capture_views(logic)
        channels = frozenset({GeneratorName.PULSE1, GeneratorName.TRIANGLE})

        logic.set_active_channels(channels)
        logic.play()

        _, kwargs = logic._service.start.call_args
        assert kwargs["active_channels"] == channels


class TestOnProjectReplaced:
    def test_on_project_replaced_stops_playback_and_resets_position(self) -> None:
        logic = _make_logic(is_open=True)
        logic._position = SongPosition(order_position=4, row_index=1)
        _capture_views(logic)

        logic.on_project_replaced()

        logic._service.stop.assert_called_once()
        assert logic._position.order_position == 0
        assert logic._position.row_index == 0


class TestSeek:
    def test_seek_forwards_order_position_to_service(self) -> None:
        logic = _make_logic(is_open=True)

        logic.seek(3)

        logic._service.seek.assert_called_once_with(3)


class TestSeekSuppression:
    def test_stale_update_before_reaching_seek_target_is_ignored(self) -> None:
        logic = _make_logic(is_open=True)
        logic._service.alive = True
        logic.on_view_changed = lambda _: None
        received: list[tuple[int, int]] = []
        logic.on_position_changed = lambda order, row: received.append((order, row))

        logic.seek(5)
        logic._on_service_result(SongPositionUpdate(position=SongPosition(order_position=2, row_index=7)))

        assert received == []

    def test_reaching_seek_target_resumes_position_updates(self) -> None:
        logic = _make_logic(is_open=True)
        logic._service.alive = True
        logic.on_view_changed = lambda _: None
        received: list[tuple[int, int]] = []
        logic.on_position_changed = lambda order, row: received.append((order, row))

        logic.seek(5)
        logic._on_service_result(SongPositionUpdate(position=SongPosition(order_position=2, row_index=7)))
        logic._on_service_result(SongPositionUpdate(position=SongPosition(order_position=5, row_index=0)))
        logic._on_service_result(SongPositionUpdate(position=SongPosition(order_position=6, row_index=0)))

        assert received == [(5, 0), (6, 0)]

    def test_seek_while_stopped_does_not_suppress_updates(self) -> None:
        logic = _make_logic(is_open=True)
        logic._service.alive = False
        logic.on_view_changed = lambda _: None
        received: list[tuple[int, int]] = []
        logic.on_position_changed = lambda order, row: received.append((order, row))

        logic.seek(5)
        logic._on_service_result(SongPositionUpdate(position=SongPosition(order_position=2, row_index=7)))

        assert received == [(2, 7)]


class TestFollowPlayback:
    def test_follow_playback_reads_session(self) -> None:
        logic = _make_logic(is_open=True)
        logic._session_manager.follow_playback = False

        assert logic.follow_playback is False

    def test_set_follow_playback_writes_session(self) -> None:
        logic = _make_logic(is_open=True)
        _capture_views(logic)

        logic.set_follow_playback(False)

        logic._session_manager.set_follow_playback.assert_called_once_with(False)

    def test_set_follow_playback_emits_view(self) -> None:
        logic = _make_logic(is_open=True)
        views = _capture_views(logic)

        logic.set_follow_playback(True)

        assert len(views) == 1

    def test_emitted_view_carries_follow_playback(self) -> None:
        logic = _make_logic(is_open=True)
        logic._session_manager.follow_playback = True
        views = _capture_views(logic)

        logic.play()

        assert views[-1].follow_playback is True
