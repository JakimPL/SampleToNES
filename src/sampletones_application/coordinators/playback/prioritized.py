from sampletones_application.coordinators.playback.protocol import AudioPlayerProtocol
from sampletones_core.audio import AudioDeviceManager


class PrioritizedPreviewPlayer:
    """Layers a primary player over device-level preview control.

    A tab whose main audio streams through a dedicated service — the sequencer
    song — shares the one output device with the one-shot tree and sample
    previews. This transport gives the primary player priority: ``play`` starts
    it, ``is_loaded`` follows it, and while the primary is engaged it owns
    pause/resume and stop. While the primary is idle those commands act on the
    shared output device, so the ``PlaybackRouter`` can pause, resume, and stop
    a sounding preview, and the state queries report either source so the
    toolbar reflects a preview as well as the primary.

    The output device reports a paused stream as still playing, so pause/resume
    checks the paused flag first, resuming a paused preview and pausing a
    playing one.
    """

    def __init__(
        self,
        primary: AudioPlayerProtocol,
        *,
        audio_device_manager: AudioDeviceManager,
    ) -> None:
        self._primary = primary
        self._audio_device_manager = audio_device_manager

    def _primary_engaged(self) -> bool:
        return self._primary.is_playing() or self._primary.is_paused()

    def play(self) -> None:
        self._primary.play()

    def pause_or_resume(self) -> None:
        if self._primary_engaged():
            self._primary.pause_or_resume()
        elif self._audio_device_manager.is_paused():
            self._audio_device_manager.resume()
        elif self._audio_device_manager.is_playing():
            self._audio_device_manager.pause()

    def stop(self) -> None:
        if self._primary_engaged():
            self._primary.stop()
        else:
            self._audio_device_manager.stop()

    def is_playing(self) -> bool:
        return self._primary.is_playing() or self._audio_device_manager.is_playing()

    def is_paused(self) -> bool:
        return self._primary.is_paused() or self._audio_device_manager.is_paused()

    def is_loaded(self) -> bool:
        return self._primary.is_loaded()
