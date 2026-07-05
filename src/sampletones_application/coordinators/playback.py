from typing import Callable, Protocol

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_core.audio import AudioDeviceManager
from sampletones_shared.exceptions import PlaybackError


class AudioPlayerProtocol(Protocol):
    def play(self) -> None: ...

    def pause_or_resume(self) -> None: ...

    def stop(self) -> None: ...

    def is_playing(self) -> bool: ...

    def is_paused(self) -> bool: ...

    def is_loaded(self) -> bool: ...


class PreviewPlayer:
    """Stop-only transport over the shared output device.

    A tab whose audio comes from one-shot tree previews exposes this player so
    the ``PlaybackRouter`` can silence a playing preview. The state queries
    mirror the output device, ``is_loaded`` reports ``False`` to keep the play
    commands reserved for tabs with a full player, and the play methods leave
    the device untouched — previews stay one-shot by design.
    """

    def __init__(self, audio_device_manager: AudioDeviceManager) -> None:
        self._audio_device_manager = audio_device_manager

    def play(self) -> None:
        return None

    def pause_or_resume(self) -> None:
        return None

    def stop(self) -> None:
        self._audio_device_manager.stop()

    def is_playing(self) -> bool:
        return self._audio_device_manager.is_playing()

    def is_paused(self) -> bool:
        return self._audio_device_manager.is_paused()

    def is_loaded(self) -> bool:
        return False


class GuardedPlayer:
    """Drives an ``AudioPlayerProtocol`` player on behalf of panels and the
    ``PlaybackRouter``, presenting playback failures as dialogs.

    Panels only fire intent hooks, so this wrapper is the coordinator-layer
    recovery boundary for the transport commands that can raise
    ``PlaybackError``; queries pass straight through.
    """

    def __init__(
        self,
        player: AudioPlayerProtocol,
        *,
        dialogs: DialogsRenderer,
        error_message: str,
    ) -> None:
        self._player = player
        self._dialogs = dialogs
        self._error_message = error_message

    def play(self) -> None:
        try:
            self._player.play()
        except PlaybackError as exception:
            self._dialogs.show_error(exception, self._error_message)

    def pause_or_resume(self) -> None:
        try:
            self._player.pause_or_resume()
        except PlaybackError as exception:
            self._dialogs.show_error(exception, self._error_message)

    def stop(self) -> None:
        self._player.stop()

    def is_playing(self) -> bool:
        return self._player.is_playing()

    def is_paused(self) -> bool:
        return self._player.is_paused()

    def is_loaded(self) -> bool:
        return self._player.is_loaded()


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
    def is_stop_enabled(self) -> bool:
        """Stop is available whenever the active tab's player reports audible output,
        covering one-shot previews that play without loading audio into the player."""
        return self._current_player_fn().is_playing()
