from typing import Dict

from pydantic import BaseModel, ConfigDict

from sampletones.audio import AudioDevice, AudioDeviceManager


class AudioSettingsData(BaseModel):
    model_config = ConfigDict(frozen=True)

    devices: Dict[int, AudioDevice]
    current_device_index: int
    current_sample_rate: int
    current_bit_depth: int

    @classmethod
    def from_device_manager(cls, device_manager: AudioDeviceManager) -> "AudioSettingsData":
        output_devices = device_manager.list_output_devices()
        current_device_index = device_manager.get_device_index()
        current_sample_rate = device_manager.get_sample_rate()
        current_bit_depth = device_manager.get_bit_depth()

        return cls(
            devices=output_devices,
            current_device_index=current_device_index,
            current_sample_rate=current_sample_rate,
            current_bit_depth=current_bit_depth,
        )

    def get_current_device(self) -> AudioDevice:
        device = self.devices.get(self.current_device_index)
        if device is None:
            raise ValueError(f"Device with index {self.current_device_index} not found")
        return device
