from typing import Callable

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.coordinators.playback.protocol import AudioPlayerProtocol


class PlaybackRouter:
    """
    Routes global playback commands to whichever tab's player is currently active.

    The active player is resolved lazily on each command, so keyboard shortcuts
    work regardless of which tab is visible.

    It holds no playback state of its own.
    """

    def __init__(
        self,
        current_player_fn: Callable[[], AudioPlayerProtocol],
        *,
        language_manager: LanguageManager,
    ) -> None:
        self._current_player_fn = current_player_fn
        self._lbl_pause = language_manager[
            Page.GLOBAL,
            Panel.MENU,
            TextType.LABEL,
            MenuElements.ITEM_PLAYBACK_PAUSE,
        ]
        self._lbl_play = language_manager[
            Page.GLOBAL,
            Panel.MENU,
            TextType.LABEL,
            MenuElements.ITEM_PLAYBACK_PLAY,
        ]
        self._lbl_resume = language_manager[
            Page.GLOBAL,
            Panel.MENU,
            TextType.LABEL,
            MenuElements.ITEM_PLAYBACK_RESUME,
        ]

    def play(self) -> None:
        self._current_player_fn().pause_or_resume()

    def play_from_start(self) -> None:
        self._current_player_fn().play()

    def stop(self) -> None:
        self._current_player_fn().stop()

    @property
    def play_label(self) -> str:
        player = self._current_player_fn()
        if player.is_loaded() and player.is_playing():
            return self._lbl_resume if player.is_paused() else self._lbl_pause

        return self._lbl_play

    @property
    def is_play_enabled(self) -> bool:
        return self._current_player_fn().is_loaded()

    @property
    def is_pause_enabled(self) -> bool:
        """Pause/resume is available while the active tab's player is sounding or held paused."""
        player = self._current_player_fn()
        return player.is_playing() or player.is_paused()

    @property
    def is_paused(self) -> bool:
        return self._current_player_fn().is_paused()

    @property
    def is_stop_enabled(self) -> bool:
        """Stop is available whenever the active tab's player reports audible output,
        covering one-shot previews that play without loading audio into the player."""
        return self._current_player_fn().is_playing()
