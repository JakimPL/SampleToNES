from typing import Callable, Optional

from sampletones.audio import AudioDeviceManager
from sampletones.constants.general import DEFAULT_SAMPLE_RATE
from sampletones.exceptions import PlaybackError
from sampletones.typehints import VoidCallback
from sampletones.utils.callbacks import CallbackMixin

from .data import AudioData


class AudioPlayer(CallbackMixin):
    def __init__(
        self,
        audio_device_manager: AudioDeviceManager,
        on_position_changed: Optional[Callable[[int], None]] = None,
        on_change_audio_state: Optional[VoidCallback] = None,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
    ):
        self.audio_device_manager = audio_device_manager
        self.audio_data: AudioData = AudioData.empty(sample_rate)

        self.on_position_changed = on_position_changed
        self.on_change_audio_state = on_change_audio_state

    def load_audio_data(self, audio_data: AudioData) -> None:
        self.audio_data = audio_data

    def clear_audio(self) -> None:
        self.stop()
        self.audio_data = AudioData.empty(self.audio_data.sample_rate)

    def _on_device_position_changed(self, position: int) -> None:
        if self.audio_data.is_loaded():
            self.audio_data.set_position(position)
            self.call(self.on_position_changed, position)

    def set_position(self, position: int) -> None:
        if self.audio_data.is_loaded():
            self.audio_data.set_position(position)
            self.audio_device_manager.set_position(position)
            self.call(self.on_position_changed, position)

    def play(self) -> None:
        if not self.audio_data.is_loaded():
            self._notify_audio_state_changed()
            return

        self.audio_device_manager.set_position_callback(self._on_device_position_changed)
        audio = self.audio_data.sample

        try:
            self.audio_device_manager.play(audio)
        except Exception as exception:
            raise PlaybackError(f"Audio playback failed: {exception}") from exception

        self._notify_audio_state_changed()

    def pause(self) -> None:
        self.audio_device_manager.pause()
        self._notify_audio_state_changed()

    def resume(self) -> None:
        self.audio_device_manager.resume()
        self._notify_audio_state_changed()

    def stop(self) -> None:
        self.audio_device_manager.stop()
        if self.audio_data.is_loaded():
            self.audio_data.reset_position()
        self.call(self.on_position_changed, 0)
        self._notify_audio_state_changed()

    @property
    def is_playing(self) -> bool:
        return self.audio_device_manager.is_playing()

    @property
    def is_paused(self) -> bool:
        return self.audio_device_manager.is_paused()

    def _notify_audio_state_changed(self) -> None:
        self.call(self.on_change_audio_state)
