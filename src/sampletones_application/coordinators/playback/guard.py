from sampletones_application.coordinators.playback.protocol import AudioPlayerProtocol
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
        self.run_guarded(self._player.play)

    def pause_or_resume(self) -> None:
        self.run_guarded(self._player.pause_or_resume)

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

    def run_guarded(self, command: VoidCallback) -> None:
        """Runs a playback command, presenting a failure to start the audio as a dialog.

        A command beyond the transport — sounding a sample from a point the reader clicked — goes
        through the same boundary the transport commands do.
        """
        try:
            command()
        except PlaybackError as exception:
            self._dialogs.show_error(exception, self._error_message)
