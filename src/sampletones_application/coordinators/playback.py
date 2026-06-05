from typing import Callable, Optional, Protocol

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.key import TextKey
from sampletones_application.categories.manager import LanguageManager


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
        *,
        language_manager: LanguageManager,
    ) -> None:
        self._current_player_fn = current_player_fn
        self._lbl_pause = language_manager[
            TextKey(
                Page.GLOBAL,
                Panel.MENU,
                TextType.LABEL,
                MenuElements.ITEM_PLAYBACK_PAUSE,
            )
        ]
        self._lbl_play = language_manager[
            TextKey(
                Page.GLOBAL,
                Panel.MENU,
                TextType.LABEL,
                MenuElements.ITEM_PLAYBACK_PLAY,
            )
        ]
        self._lbl_resume = language_manager[
            TextKey(
                Page.GLOBAL,
                Panel.MENU,
                TextType.LABEL,
                MenuElements.ITEM_PLAYBACK_RESUME,
            )
        ]

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
            return self._lbl_resume if player.is_paused() else self._lbl_pause

        return self._lbl_play

    @property
    def is_play_enabled(self) -> bool:
        player = self._current_player_fn()
        return player is not None and player.is_loaded()

    @property
    def is_stop_enabled(self) -> bool:
        player = self._current_player_fn()
        return player is not None and player.is_loaded() and player.is_playing()
