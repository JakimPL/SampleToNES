from sampletones_application.coordinators.playback.protocol import (
    AudioPlayerProtocol,
    SamplePlayerProtocol,
)
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_shared.exceptions import PlaybackError
from sampletones_shared.types.callback import VoidCallback


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
        self._guard(self._player.play)

    def pause_or_resume(self) -> None:
        self._guard(self._player.pause_or_resume)

    def stop(self) -> None:
        self._player.stop()

    def is_playing(self) -> bool:
        return self._player.is_playing()

    def is_paused(self) -> bool:
        return self._player.is_paused()

    def is_engaged(self) -> bool:
        return self._player.is_engaged()

    def is_loaded(self) -> bool:
        return self._player.is_loaded()

    def _guard(self, command: VoidCallback) -> None:
        try:
            command()
        except PlaybackError as exception:
            self._dialogs.show_error(exception, self._error_message)


class GuardedSamplePlayer(GuardedPlayer):
    """Drives a player of one stretch of audio, which also takes the playhead to a sample the reader
    points at, presenting a failure to start there as the transport commands do."""

    def __init__(
        self,
        player: SamplePlayerProtocol,
        *,
        dialogs: DialogsRenderer,
        error_message: str,
    ) -> None:
        super().__init__(
            player,
            dialogs=dialogs,
            error_message=error_message,
        )
        self._sample_player = player

    def play_from(self, position: int) -> None:
        self._guard(lambda: self._sample_player.play_from(position))
