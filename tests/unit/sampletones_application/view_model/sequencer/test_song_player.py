from typing import Optional

import pytest
from pydantic import ValidationError

from sampletones_application.view_model.sequencer.song_player import SongPlayerViewModel


def _view_model(
    *,
    is_loaded: bool = True,
    is_playing: bool = False,
    is_paused: bool = False,
    follow_playback: bool = True,
    order_position: int = 0,
    row_index: int = 0,
    error: Optional[str] = None,
) -> SongPlayerViewModel:
    return SongPlayerViewModel(
        is_loaded=is_loaded,
        is_playing=is_playing,
        is_paused=is_paused,
        follow_playback=follow_playback,
        order_position=order_position,
        row_index=row_index,
        error=error,
    )


class TestSongPlayerViewModelProperties:
    def test_play_enabled_when_loaded(self) -> None:
        assert _view_model(is_loaded=True).play_enabled is True

    def test_play_disabled_when_not_loaded(self) -> None:
        assert _view_model(is_loaded=False).play_enabled is False

    def test_stop_enabled_when_loaded_and_playing(self) -> None:
        assert _view_model(is_loaded=True, is_playing=True).stop_enabled is True

    def test_stop_disabled_when_not_playing(self) -> None:
        assert _view_model(is_loaded=True, is_playing=False).stop_enabled is False

    def test_stop_disabled_when_not_loaded(self) -> None:
        assert _view_model(is_loaded=False, is_playing=True).stop_enabled is False

    def test_error_defaults_to_none(self) -> None:
        assert _view_model().error is None

    def test_error_preserved(self) -> None:
        vm = _view_model(error="stream error")
        assert vm.error == "stream error"

    def test_position_fields_stored(self) -> None:
        vm = _view_model(order_position=3, row_index=7)
        assert vm.order_position == 3
        assert vm.row_index == 7


class TestSongPlayerViewModelFrozen:
    def test_assignment_raises(self) -> None:
        vm = _view_model()
        with pytest.raises(ValidationError):
            vm.is_playing = True  # type: ignore[misc]


@pytest.mark.parametrize(
    "is_loaded, is_playing, play_enabled, stop_enabled",
    [
        (True, True, True, True),
        (True, False, True, False),
        (False, True, False, False),
        (False, False, False, False),
    ],
    ids=["loaded_playing", "loaded_stopped", "unloaded_playing", "unloaded_stopped"],
)
def test_button_states_parametrized(
    is_loaded: bool,
    is_playing: bool,
    play_enabled: bool,
    stop_enabled: bool,
) -> None:
    vm = _view_model(is_loaded=is_loaded, is_playing=is_playing)
    assert vm.play_enabled is play_enabled
    assert vm.stop_enabled is stop_enabled
