from typing import Callable, Optional

from sampletones.audio import AudioDeviceManager
from sampletones.constants.general import DEFAULT_SAMPLE_RATE
from sampletones.exceptions import PlaybackError
from sampletones.utils.logger import logger

from .data import AudioData


class AudioPlayer:
    def __init__(
        self,
        audio_device_manager: AudioDeviceManager,
        on_position_changed: Optional[Callable[[int], None]] = None,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
    ):
        self.audio_device_manager = audio_device_manager
        self.audio_data: AudioData = AudioData.empty(sample_rate)
        self.on_position_changed = on_position_changed

    def load_audio_data(self, audio_data: AudioData) -> None:
        self.audio_data = audio_data

    def clear_audio(self) -> None:
        self.stop()
        self.audio_data = AudioData.empty(self.audio_data.sample_rate)

    def _on_device_position_changed(self, position: int) -> None:
        if self.audio_data.is_loaded():
            self.audio_data.set_position(position)
        if self.on_position_changed:
            self.on_position_changed(position)

    def set_position(self, position: int) -> None:
        if self.audio_data.is_loaded():
            self.audio_data.set_position(position)
            self.audio_device_manager.set_position(position)
            if self.on_position_changed:
                self.on_position_changed(position)

    def play(self) -> None:
        if not self.audio_data.is_loaded():
            raise PlaybackError("No audio loaded")

        self.audio_device_manager.set_position_callback(self._on_device_position_changed)
        audio = self.audio_data.sample

        try:
            self.audio_device_manager.play(audio)
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, "Audio playback failed")
            raise PlaybackError(str(exception)) from exception

    def pause(self) -> None:
        self.audio_device_manager.pause()

    def resume(self) -> None:
        self.audio_device_manager.resume()

    def stop(self) -> None:
        self.audio_device_manager.stop()
        if self.audio_data.is_loaded():
            self.audio_data.reset_position()
        if self.on_position_changed:
            self.on_position_changed(0)

    @property
    def is_playing(self) -> bool:
        return self.audio_device_manager.is_playing()

    @property
    def is_paused(self) -> bool:
        return self.audio_device_manager.is_paused()
