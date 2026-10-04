from sampletones_application.coordinators.playback.failures import PlaybackFailurePresenter
from sampletones_application.coordinators.playback.protocol import AudioPlayerProtocol
from sampletones_shared.exceptions import PlaybackError
from sampletones_shared.types.callback import VoidCallback


class GuardedPlayer:
    """Drives an ``AudioPlayerProtocol`` player on behalf of panels and the
    ``PlaybackRouter``, handing playback failures to the presenter.

    Panels only fire intent hooks, so this wrapper is the coordinator-layer
    recovery boundary for the transport commands that can raise
    ``PlaybackError``; queries pass straight through.
    """

    def __init__(
        self,
        player: AudioPlayerProtocol,
        *,
        failures: PlaybackFailurePresenter,
        error_message: str,
    ) -> None:
        self._player = player
        self._failures = failures
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
        """Runs a playback command, showing the reader a failure to start the audio.

        A command beyond the transport — sounding a sample from a point the reader clicked — goes
        through the same boundary the transport commands do.
        """
        try:
            command()
        except PlaybackError as exception:
            self._failures.present(exception, message=self._error_message)
