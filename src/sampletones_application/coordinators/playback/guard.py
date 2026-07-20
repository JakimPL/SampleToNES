from sampletones_application.coordinators.playback.protocol import AudioPlayerProtocol
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_shared.exceptions import PlaybackError


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
