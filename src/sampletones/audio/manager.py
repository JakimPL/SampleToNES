import threading
from typing import Callable, Dict, Optional

import numpy as np
import pyaudio

from sampletones.utils.logger import logger

from .device import (
    BIT_DEPTHS,
    DEFAULT_BIT_DEPTH,
    SAMPLE_RATES,
    AudioDevice,
    BitDepth,
    CurrentDevice,
    SampleRate,
)

CHANNELS = 1
FORMAT = pyaudio.paFloat32
CHUNK_SIZE = 1024


class AudioDeviceManager:
    def __init__(self) -> None:
        self._pyaudio = pyaudio.PyAudio()
        self._devices: Dict[int, AudioDevice] = {}

        self._device_index: Optional[int] = None
        self._sample_rate: Optional[SampleRate] = None
        self._bit_depth: Optional[BitDepth] = None

        self._audio_data: Optional[np.ndarray] = None
        self._position: int = 0
        self._playing: bool = False
        self._paused: bool = False
        self._position_callback: Optional[Callable[[int], None]] = None
        self._playback_thread: Optional[threading.Thread] = None
        self._stop_flag: bool = False

        self.refresh_devices()
        self._initialize_default_device()
        logger.debug("AudioDeviceManager initialized")

    def refresh_devices(self) -> None:
        try:
            default_input_index = int(self._pyaudio.get_default_input_device_info()["index"])
        except IOError:
            default_input_index = -1

        try:
            default_output_index = int(self._pyaudio.get_default_output_device_info()["index"])
        except IOError:
            default_output_index = -1

        self._devices: Dict[int, AudioDevice] = {}
        for i in range(self._pyaudio.get_device_count()):
            info = self._pyaudio.get_device_info_by_index(i)
            if int(info["maxOutputChannels"]) == 0:
                continue

            default_sample_rate: SampleRate = int(info["defaultSampleRate"])
            supported_rates = sorted(set(SAMPLE_RATES) | {default_sample_rate})

            self._devices[i] = AudioDevice(
                index=i,
                name=str(info["name"]),
                is_input=int(info["maxInputChannels"]) > 0,
                is_output=True,
                is_default_input=i == default_input_index,
                is_default_output=i == default_output_index,
                default_sample_rate=default_sample_rate,
                supported_sample_rates=supported_rates,
                supported_bit_depths=[DEFAULT_BIT_DEPTH],
            )

    def _initialize_default_device(self) -> None:
        try:
            info = self._pyaudio.get_default_output_device_info()
            device_index = int(info["index"])
            if device_index in self._devices:
                device = self._devices[device_index]
                self._device_index = device_index
                self._sample_rate = device.default_sample_rate
                self._bit_depth = DEFAULT_BIT_DEPTH
        except IOError:
            logger.warning("No default output device found")

    @property
    def device_index(self) -> int:
        if self._device_index is None:
            raise ValueError("No audio device selected")
        return self._device_index

    @device_index.setter
    def device_index(self, value: int) -> None:
        if value not in self._devices:
            raise ValueError(f"Device with index {value} not found")

        self.stop()
        device = self._devices[value]
        self._device_index = value
        self._sample_rate = device.default_sample_rate
        self._bit_depth = DEFAULT_BIT_DEPTH

    @property
    def device_name(self) -> str:
        return self._devices[self.device_index].name

    @property
    def sample_rate(self) -> SampleRate:
        if self._sample_rate is None:
            raise ValueError("No audio device selected")

        return self._sample_rate

    @sample_rate.setter
    def sample_rate(self, value: SampleRate) -> None:
        if not value in SAMPLE_RATES:
            raise ValueError(f"Sample rate {value} is not valid")

        device = self._devices[self.device_index]
        if value not in device.supported_sample_rates:
            raise ValueError(f"Sample rate {value} not supported by device {device.name}")

        self._sample_rate = value

    @property
    def bit_depth(self) -> BitDepth:
        if self._bit_depth is None:
            raise ValueError("No audio device selected")

        return self._bit_depth

    @bit_depth.setter
    def bit_depth(self, value: BitDepth) -> None:
        if not value in BIT_DEPTHS:
            raise ValueError(f"Bit depth {value} is not valid")

        device = self._devices[self.device_index]
        if value not in device.supported_bit_depths:
            raise ValueError(f"Bit depth {value} not supported by device {device.name}")

        self._bit_depth = value

    def get_current_device(self) -> CurrentDevice:
        return CurrentDevice(
            device_index=self.device_index,
            name=self.device_name,
            sample_rate=self.sample_rate,
            bit_depth=self.bit_depth,
        )

    def list_devices(self) -> Dict[int, AudioDevice]:
        return dict(self._devices)

    def configure_device(self, device_index: int, sample_rate: int, bit_depth: int) -> None:
        self.stop()
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth
        logger.info(
            f"Audio device configured: {self.device_name} "
            f"(index={device_index}, sample_rate={sample_rate}, bit_depth={bit_depth})"
        )

    def set_position_callback(self, callback: Optional[Callable[[int], None]]) -> None:
        self._position_callback = callback

    def set_position(self, position: int) -> None:
        if self._audio_data is not None:
            self._position = max(0, min(position, len(self._audio_data)))

    def play(self, audio: np.ndarray) -> None:
        self.stop()
        self._audio_data = audio.astype(np.float32)
        self._position = 0
        self._playing = True
        self._paused = False
        self._stop_flag = False
        self._playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
        self._playback_thread.start()

    def _playback_worker(self) -> None:
        stream = self._pyaudio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=self.sample_rate,
            output=True,
            output_device_index=self._device_index,
        )

        while not self._stop_flag and self._audio_data is not None:
            if self._paused:
                continue

            remaining = len(self._audio_data) - self._position
            if remaining <= 0:
                break

            chunk_size = min(CHUNK_SIZE, remaining)
            chunk = self._audio_data[self._position : self._position + chunk_size]
            stream.write(chunk.tobytes())
            self._position += chunk_size

            if self._position_callback:
                self._position_callback(self._position)

        stream.stop_stream()
        stream.close()
        self._playing = False

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        self._stop_flag = True
        if self._playback_thread is not None:
            self._playback_thread.join(timeout=1.0)

        self._playback_thread = None
        self._playing = False
        self._paused = False
        self._position = 0
        self._audio_data = None

        if self._position_callback:
            self._position_callback(0)

    def is_playing(self) -> bool:
        return self._playing

    def is_paused(self) -> bool:
        return self._paused

    def terminate(self) -> None:
        self.stop()
        self._pyaudio.terminate()
