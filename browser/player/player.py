from typing import Callable, Optional

import numpy as np

from browser.player.data import AudioData
from constants.general import SAMPLE_RATE
from utils.audio.device import AudioDeviceManager
from utils.audio.io import clip_audio, stereo_to_mono


class PlaybackError(Exception):
    pass


class AudioPlayer:
    def __init__(
        self,
        audio_device_manager: AudioDeviceManager,
        on_position_changed: Optional[Callable[[int], None]] = None,
        sample_rate: int = SAMPLE_RATE,
    ):
        self.audio_device_manager = audio_device_manager
        self.audio_data: AudioData = AudioData.empty(sample_rate)
        self.on_position_changed = on_position_changed
        self.audio_device_manager.set_position_callback(on_position_changed)

    def load_audio_data(self, audio_data: AudioData) -> None:
        self.audio_data = audio_data

    def clear_audio(self) -> None:
        self.stop()
        self.audio_data = AudioData.empty(self.audio_data.sample_rate)

    def set_position(self, position: int) -> None:
        if self.audio_data.is_loaded():
            self.audio_data.set_position(position)
            self.audio_device_manager.set_position(position)
            if self.on_position_changed:
                self.on_position_changed(position)

    def play(self) -> None:
        if not self.audio_data.is_loaded():
            raise PlaybackError("no audio loaded")

        try:
            audio = self.audio_data.sample
            audio = stereo_to_mono(audio)
            audio = clip_audio(audio)
            audio = audio.astype(np.float32)
            self.audio_device_manager.play(audio)
        except Exception as exception:
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
