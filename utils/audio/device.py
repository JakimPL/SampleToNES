from typing import Any, List, Optional

import numpy as np
import sounddevice as sd
from pydantic import BaseModel


class AudioDevice(BaseModel):
    index: int
    name: str
    is_input: bool
    is_output: bool
    is_default_input: bool
    is_default_output: bool

    class Config:
        frozen = True


class AudioDeviceManager:
    def __init__(self):
        self._current_device: Optional[int] = None
        self._device_sample_rate: Optional[int] = None
        self._set_default_device()

    def _set_default_device(self) -> None:
        default_output = sd.default.device[1]
        if default_output is not None:
            self.set_device(default_output)

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
        self._current_device = device_index
        device_info = sd.query_devices(device_index)
        device_info_any: Any = device_info
        self._device_sample_rate = int(device_info_any["default_samplerate"])

    def get_device(self) -> Optional[int]:
        return self._current_device

    def start(self, audio: np.ndarray) -> None:
        sd.play(audio, samplerate=self._device_sample_rate, device=self._current_device)

    def stop(self) -> None:
        sd.stop()

    def pause(self) -> None:
        sd.stop()
