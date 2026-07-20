from sampletones_core.audio import AudioDeviceManager


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
