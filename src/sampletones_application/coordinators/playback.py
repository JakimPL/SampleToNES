from typing import Callable, Optional, Protocol

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager


class AudioPlayerPanelProtocol(Protocol):
    def play(self) -> None: ...

    def pause_or_resume(self) -> None: ...

    def stop(self) -> None: ...

    def is_playing(self) -> bool: ...

    def is_paused(self) -> bool: ...

    def is_loaded(self) -> bool: ...


class PlaybackRouter:
    """Routes play/pause/stop commands to whichever tab currently has a player.

    Multiple tabs (Reconstructions, Instructions, Sequencer) each own an audio
    player panel.  Global keyboard shortcuts for playback (Space, Shift+Space,
    Ctrl+Space) should operate on the active tab's player without knowing which
    tab is active.  ``PlaybackRouter`` encapsulates that dispatch logic.

    Responsibilities:
    - Forward ``play``, ``play_from_start``, and ``stop`` to the currently
      active player panel (resolved lazily via ``current_player_fn``).
    - Compute the correct label for the play/pause menu item
      (``play_label``: "Play", "Pause", or "Resume" depending on playback state).
    - Compute ``is_play_enabled`` and ``is_stop_enabled`` for menu bar state.

    Governing principles:
    - Stateless: holds no playback state of its own.  All state is read
      from the player panel resolved by ``current_player_fn`` on each call.
    - Does not import from ``ui/`` or ``logic/`` directly; it communicates
      with player panels through the ``AudioPlayerPanelProtocol`` structural
      protocol, keeping the coupling minimal.
    - Does not call DPG.

    Dependencies: ``AudioPlayerPanelProtocol`` (Protocol), ``LanguageManager``.
    """

    def __init__(
        self,
        current_player_fn: Callable[[], Optional[AudioPlayerPanelProtocol]],
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
