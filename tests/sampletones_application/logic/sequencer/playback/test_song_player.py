from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from sampletones_application.logic.sequencer.playback.song_player import SongPlayerLogic
from sampletones_application.logic.sequencer.playback.synthesizer import RowSynthesizer
from sampletones_application.services.song_player import SongPlayerService
from sampletones_application.services.song_player_result import (
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
    audio_device_manager = MagicMock()
    return SongPlayerLogic(audio_device_manager, controller, Config())


def _capture_view(logic: SongPlayerLogic) -> list[SongPlayerViewModel]:
    views: list[SongPlayerViewModel] = []
    logic.on_view_changed = views.append
    return views


class TestSongPlayerLogicStateProps:
    def test_is_loaded_when_project_open(self) -> None:
        logic = _make_logic(is_open=True)
        assert logic.is_loaded() is True

    def test_is_not_loaded_when_project_closed(self) -> None:
        logic = _make_logic(is_open=False)
        assert logic.is_loaded() is False

    def test_is_not_playing_initially(self) -> None:
        logic = _make_logic()
        assert logic.is_playing() is False

    def test_is_not_paused_initially(self) -> None:
        logic = _make_logic()
        assert logic.is_paused() is False


class TestSongPlayerLogicPlay:
    def test_play_does_nothing_when_project_not_open(self) -> None:
        logic = _make_logic(is_open=False)
        views = _capture_view(logic)
        with patch.object(SongPlayerService, "start") as mock_start:
            logic.play()
            mock_start.assert_not_called()
        assert not views

    def test_play_starts_service_when_project_open(self) -> None:
        logic = _make_logic(is_open=True)
        with patch.object(SongPlayerService, "start") as mock_start, patch.object(SongPlayerService, "stop"):
            logic.play()
            mock_start.assert_called_once()

    def test_play_clears_last_error(self) -> None:
        logic = _make_logic(is_open=True)
        logic._last_error = "previous error"
        with patch.object(SongPlayerService, "start"), patch.object(SongPlayerService, "stop"):
            logic.play()
        assert logic._last_error is None

    def test_play_resets_position_to_zero(self) -> None:
        logic = _make_logic(is_open=True)
        logic._position = SongPosition(order_position=3, row_index=5)
        with patch.object(SongPlayerService, "start"), patch.object(SongPlayerService, "stop"):
            logic.play()
        assert logic._position.order_position == 0
        assert logic._position.row_index == 0

    def test_play_emits_view(self) -> None:
        logic = _make_logic(is_open=True)
        views = _capture_view(logic)
        with patch.object(SongPlayerService, "start"), patch.object(SongPlayerService, "stop"):
            logic.play()
        assert len(views) == 1


class TestSongPlayerLogicPlayFrom:
    def test_play_from_sets_position_before_play(self) -> None:
        logic = _make_logic(is_open=True)
        with patch.object(SongPlayerService, "start"), patch.object(SongPlayerService, "stop"):
            logic.play_from(order_position=2, row_index=4)
        assert logic._position.order_position == 2
        assert logic._position.row_index == 4


class TestSongPlayerLogicStop:
    def test_stop_resets_position(self) -> None:
        logic = _make_logic(is_open=True)
        logic._position = SongPosition(order_position=5, row_index=3)
        with patch.object(SongPlayerService, "stop"):
            logic.stop()
        assert logic._position.order_position == 0
        assert logic._position.row_index == 0

    def test_stop_calls_service_stop(self) -> None:
        logic = _make_logic(is_open=True)
        with patch.object(SongPlayerService, "stop") as mock_stop:
            logic.stop()
            mock_stop.assert_called_once()

    def test_stop_emits_view(self) -> None:
        logic = _make_logic(is_open=True)
        views = _capture_view(logic)
        with patch.object(SongPlayerService, "stop"):
            logic.stop()
        assert len(views) == 1


class TestSongPlayerLogicPauseResume:
    def test_pause_or_resume_plays_when_idle_and_loaded(self) -> None:
        logic = _make_logic(is_open=True)
        with (
            patch.object(SongPlayerService, "is_paused", new_callable=lambda: property(lambda self: False)),
            patch.object(SongPlayerService, "is_playing", new_callable=lambda: property(lambda self: False)),
            patch.object(SongPlayerService, "start") as mock_start,
            patch.object(SongPlayerService, "stop"),
        ):
            logic.pause_or_resume()
            mock_start.assert_called_once()

    def test_pause_or_resume_resumes_when_paused(self) -> None:
        logic = _make_logic(is_open=True)
        with (
            patch.object(SongPlayerService, "is_paused", new_callable=lambda: property(lambda self: True)),
            patch.object(SongPlayerService, "resume") as mock_resume,
        ):
            logic.pause_or_resume()
            mock_resume.assert_called_once()

    def test_pause_or_resume_pauses_when_playing(self) -> None:
        logic = _make_logic(is_open=True)
        with (
            patch.object(SongPlayerService, "is_paused", new_callable=lambda: property(lambda self: False)),
            patch.object(SongPlayerService, "is_playing", new_callable=lambda: property(lambda self: True)),
            patch.object(SongPlayerService, "pause") as mock_pause,
        ):
            logic.pause_or_resume()
            mock_pause.assert_called_once()


class TestSongPlayerLogicSetActiveChannels:
    def test_set_active_channels_stores_value(self) -> None:
        logic = _make_logic()
        channels = frozenset({GeneratorName.PULSE1, GeneratorName.TRIANGLE})
        logic.set_active_channels(channels)
        assert logic._active_channels == channels


class TestSongPlayerLogicOnProjectReplaced:
    def test_on_project_replaced_calls_stop(self) -> None:
        logic = _make_logic(is_open=True)
        with patch.object(SongPlayerService, "stop") as mock_stop:
            logic.on_project_replaced()
            mock_stop.assert_called_once()


class TestSongPlayerLogicOnServiceResult:
    def test_position_update_stores_position_and_calls_on_position_changed(self) -> None:
        logic = _make_logic()
        received: list[tuple[int, int]] = []
        logic.on_position_changed = lambda order, row: received.append((order, row))
        logic.on_view_changed = lambda vm: None

        position = SongPosition(order_position=2, row_index=5)
        logic._on_service_result(SongPositionUpdate(position=position))

        assert logic._position.order_position == 2
        assert logic._position.row_index == 5
        assert received == [(2, 5)]

    def test_position_update_emits_view(self) -> None:
        logic = _make_logic()
        views = _capture_view(logic)
        logic.on_position_changed = lambda order, row: None

        logic._on_service_result(SongPositionUpdate(position=SongPosition(order_position=1, row_index=0)))

        assert len(views) == 1

    def test_playback_stopped_emits_view(self) -> None:
        logic = _make_logic()
        views = _capture_view(logic)
        logic._on_service_result(SongPlaybackStopped())
        assert len(views) == 1

    def test_playback_error_stores_error_message(self) -> None:
        logic = _make_logic()
        logic.on_view_changed = lambda vm: None
        logic.on_error = lambda error: None

        logic._on_service_result(SongPlaybackError(error=ValueError("stream failed")))

        assert logic._last_error == "stream failed"

    def test_playback_error_uses_type_name_when_str_empty(self) -> None:
        logic = _make_logic()
        logic.on_view_changed = lambda vm: None
        logic.on_error = lambda error: None

        class NoMessageError(Exception):
            pass

        logic._on_service_result(SongPlaybackError(error=NoMessageError()))

        assert logic._last_error == "NoMessageError"

    def test_playback_error_resets_position(self) -> None:
        logic = _make_logic()
        logic.on_view_changed = lambda vm: None
        logic.on_error = lambda error: None
        logic._position = SongPosition(order_position=3, row_index=2)

        logic._on_service_result(SongPlaybackError(error=RuntimeError("fail")))

        assert logic._position.order_position == 0
        assert logic._position.row_index == 0

    def test_playback_error_calls_on_error_callback(self) -> None:
        logic = _make_logic()
        logic.on_view_changed = lambda vm: None
        errors: list[Exception] = []
        logic.on_error = errors.append

        error = RuntimeError("playback failed")
        logic._on_service_result(SongPlaybackError(error=error))

        assert errors == [error]

    def test_playback_error_emits_view(self) -> None:
        logic = _make_logic()
        views = _capture_view(logic)
        logic.on_error = lambda error: None

        logic._on_service_result(SongPlaybackError(error=RuntimeError("fail")))

        assert len(views) == 1


class TestSongPlayerLogicBuildViewModel:
    def test_view_model_reflects_loaded_state(self) -> None:
        logic = _make_logic(is_open=True)
        vm = logic._build_view_model()
        assert vm.is_loaded is True

    def test_view_model_error_is_none_initially(self) -> None:
        logic = _make_logic()
        vm = logic._build_view_model()
        assert vm.error is None

    def test_view_model_error_after_playback_error(self) -> None:
        logic = _make_logic()
        logic._last_error = "device error"
        vm = logic._build_view_model()
        assert vm.error == "device error"

    def test_view_model_position_matches_internal_state(self) -> None:
        logic = _make_logic()
        logic._position = SongPosition(order_position=4, row_index=7)
        vm = logic._build_view_model()
        assert vm.order_position == 4
        assert vm.row_index == 7
