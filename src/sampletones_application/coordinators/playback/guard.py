from sampletones_application.coordinators.playback.failures import PlaybackFailurePresenter
from sampletones_application.coordinators.playback.protocol import AudioPlayerProtocol
from sampletones_application.logic.shared.previews import DocumentPreviews
from sampletones_shared.exceptions import PlaybackError
from sampletones_shared.types.callback import VoidCallback


class GuardedPlayer:
    """Drives an ``AudioPlayerProtocol`` player on behalf of panels and the
    ``PlaybackRouter``, handing playback failures to the presenter.

    Panels only fire intent hooks, so this wrapper is the coordinator-layer
    recovery boundary for the transport commands that can raise
    ``PlaybackError``; queries pass straight through. A start that fails at once
    reads the way a failure on the playing thread does. Every command here is
    playback the reader asked for, so each forgets a preview still on its way:
    the sound the reader asked for last is the one that takes the device.
    """

    def __init__(
        self,
        player: AudioPlayerProtocol,
        *,
        failures: PlaybackFailurePresenter,
        previews: DocumentPreviews,
    ) -> None:
        self._player = player
        self._failures = failures
        self._previews = previews

    def play(self) -> None:
        self.run_guarded(self._player.play)

    def pause_or_resume(self) -> None:
        self.run_guarded(self._player.pause_or_resume)

    def stop(self) -> None:
        self._previews.cancel()
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
        through the same boundary the transport commands do, and forgets a preview on its way the
        same way.
        """
        self._previews.cancel()
        try:
            command()
        except PlaybackError as exception:
            self._failures.present_playing_failure(exception)
