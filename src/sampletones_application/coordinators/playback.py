from typing import Callable, Optional, Protocol

from sampletones_application.constants.general import (
    LBL_MENU_ITEM_PLAYBACK_PAUSE,
    LBL_MENU_ITEM_PLAYBACK_PLAY,
    LBL_MENU_ITEM_PLAYBACK_RESUME,
)


class AudioPlayerPanelProtocol(Protocol):
    def play(self) -> None: ...

    def pause_or_resume(self) -> None: ...

    def stop(self) -> None: ...

    def is_playing(self) -> bool: ...

    def is_paused(self) -> bool: ...

    def is_loaded(self) -> bool: ...


class PlaybackRouter:
    def __init__(
        self,
        current_player_fn: Callable[[], Optional[AudioPlayerPanelProtocol]],
    ) -> None:
        self._current_player_fn = current_player_fn

    def play(self) -> None:
        player = self._current_player_fn()
        if player is not None:
            player.pause_or_resume()

    def play_from_start(self) -> None:
        player = self._current_player_fn()
        if player is not None:
            player.play()

    def stop(self) -> None:
        player = self._current_player_fn()
        if player is not None:
            player.stop()

    @property
    def play_label(self) -> str:
        player = self._current_player_fn()
        if player is not None and player.is_loaded() and player.is_playing():
            return LBL_MENU_ITEM_PLAYBACK_RESUME if player.is_paused() else LBL_MENU_ITEM_PLAYBACK_PAUSE

        return LBL_MENU_ITEM_PLAYBACK_PLAY

    @property
    def is_play_enabled(self) -> bool:
        player = self._current_player_fn()
        return player is not None and player.is_loaded()

    @property
    def is_stop_enabled(self) -> bool:
        player = self._current_player_fn()
        return player is not None and player.is_loaded() and player.is_playing()
