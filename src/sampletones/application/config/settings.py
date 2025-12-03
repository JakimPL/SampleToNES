from typing import Dict

from pydantic import BaseModel, ConfigDict

from sampletones.audio import AudioDevice, AudioDeviceManager, BitDepth, SampleRate


class AudioSettingsData(BaseModel):
    model_config = ConfigDict(frozen=True)

    devices: Dict[int, AudioDevice]
    device_index: int
    device_name: str
    sample_rate: SampleRate
    bit_depth: BitDepth

    @classmethod
    def from_device_manager(cls, audio_device_manager: AudioDeviceManager) -> "AudioSettingsData":
        output_devices = audio_device_manager.list_devices()
        current_device = audio_device_manager.get_current_device()

        return cls(
            devices=output_devices,
            device_index=current_device.device_index,
            device_name=current_device.name,
            sample_rate=current_device.sample_rate,
            bit_depth=current_device.bit_depth,
        )

    def get_current_device(self) -> AudioDevice:
        device = self.devices.get(self.device_index)
        if device is None:
            raise ValueError(f"Device with index {self.device_index} not found")
        return device
