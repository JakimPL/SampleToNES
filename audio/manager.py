import threading
from typing import Any, Callable, List, Optional

import numpy as np
import sounddevice as sd

from audio.device import AudioDevice


class AudioDeviceManager:
    def __init__(self):
        self._current_device: Optional[int] = None
        self._device_sample_rate: Optional[int] = None
        self._stream: Optional[sd.OutputStream] = None
        self._audio_data: Optional[np.ndarray] = None
        self._position: int = 0
        self._is_playing: bool = False
        self._is_paused: bool = False
        self._on_position_changed: Optional[Callable[[int], None]] = None
        self._lock = threading.Lock()
        self._set_default_device()

    def _set_default_device(self) -> None:
        devices = sd.query_devices()
        default_output = sd.default.device[1]

        if default_output is None and devices:
            for i, device in enumerate(devices):
                device_any: Any = device
                if int(device_any["max_output_channels"]) > 0:
                    default_output = i
                    break

        if default_output is not None:
            self.set_device(default_output)

    def _audio_callback(
        self,
        outdata: np.ndarray,
        frames: int,
        time_info: Any,
        status: sd.CallbackFlags,
    ) -> None:
        should_stop = False
        callback = None
        position = 0
        chunk_size = 0
        chunk_data = np.array([])

        with self._lock:
            if self._audio_data is None or not self._is_playing:
                outdata.fill(0)
                return

            remaining = len(self._audio_data) - self._position

            if remaining <= 0:
                outdata.fill(0)
                self._is_playing = False
                self._is_paused = False
                position = len(self._audio_data)
                self._position = position
                callback = self._on_position_changed
                should_stop = True
            else:
                chunk_size = min(frames, remaining)
                chunk_data = self._audio_data[self._position : self._position + chunk_size].copy()
                self._position += chunk_size
                position = self._position
                callback = self._on_position_changed

        if should_stop:
            if callback:
                callback(position)
            raise sd.CallbackStop()

        outdata[:chunk_size] = chunk_data.reshape(-1, 1)

        if chunk_size < frames:
            outdata[chunk_size:].fill(0)

        if callback:
            callback(position)

    def list_devices(self) -> List[AudioDevice]:
        devices = sd.query_devices()
        default_input = sd.default.device[0]
        default_output = sd.default.device[1]

        result = []
        for i, device in enumerate(devices):
            device_any: Any = device
            max_input_channels = int(device_any["max_input_channels"])
            max_output_channels = int(device_any["max_output_channels"])
            device_name = str(device_any["name"])

            result.append(
                AudioDevice(
                    index=i,
                    name=device_name,
                    is_input=max_input_channels > 0,
                    is_output=max_output_channels > 0,
                    is_default_input=i == default_input,
                    is_default_output=i == default_output,
                )
            )

        return result

    def set_device(self, device_index: int) -> None:
        self.stop()
        self._current_device = device_index
        device_info = sd.query_devices(device_index)
        device_info_any: Any = device_info
        self._device_sample_rate = int(device_info_any["default_samplerate"])

    def get_device(self) -> Optional[int]:
        return self._current_device

    def set_position_callback(self, callback: Optional[Callable[[int], None]]) -> None:
        self._on_position_changed = callback

    def get_position(self) -> int:
        return self._position

    def set_position(self, position: int) -> None:
        with self._lock:
            assert self._audio_data is not None
            self._position = max(0, min(position, len(self._audio_data)))
            callback = self._on_position_changed
            current_position = self._position

        if callback:
            callback(current_position)

    def play(self, audio: np.ndarray, from_position: Optional[int] = None) -> None:
        with self._lock:
            if self._stream is not None:
                stream = self._stream
                self._stream = None
            else:
                stream = None

        if stream is not None:
            stream.stop()
            stream.close()

        with self._lock:
            self._audio_data = audio
            self._position = from_position if from_position is not None else 0
            self._is_playing = True
            self._is_paused = False

            self._stream = sd.OutputStream(
                samplerate=self._device_sample_rate,
                channels=1,
                callback=self._audio_callback,
                device=self._current_device,
                dtype=np.float32,
            )
            self._stream.start()

    def pause(self) -> None:
        with self._lock:
            self._is_playing = False
            self._is_paused = True

    def resume(self) -> None:
        with self._lock:
            self._is_playing = True
            self._is_paused = False

    def stop(self) -> None:
        with self._lock:
            self._is_playing = False
            self._is_paused = False
            self._position = 0

            if self._stream is not None:
                stream = self._stream
                self._stream = None
            else:
                stream = None

            self._audio_data = None
            callback = self._on_position_changed

        if stream is not None:
            stream.stop()
            stream.close()

        if callback:
            callback(0)

    def is_playing(self) -> bool:
        with self._lock:
            return self._is_playing

    def is_paused(self) -> bool:
        with self._lock:
            return self._is_paused
