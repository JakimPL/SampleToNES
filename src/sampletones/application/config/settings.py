from typing import List

from pydantic import BaseModel, ConfigDict

from sampletones.audio import AudioDeviceManager


class AudioSettingsData(BaseModel):
    model_config = ConfigDict(frozen=True)

    device_names: List[str]
    device_indices: List[int]
    current_device_index: int
    current_device_name: str
    sample_rates: List[int]
    current_sample_rate: int
    bit_depths: List[int]
    current_bit_depth: int

    @classmethod
    def from_device_manager(cls, device_manager: AudioDeviceManager) -> "AudioSettingsData":
        output_devices = device_manager.list_output_devices()
        device_names = [device.name for device in output_devices]
        device_indices = [device.index for device in output_devices]

        current_device_index = device_manager.get_device_index()
        current_device_name = device_manager.get_device_name()
        sample_rates = device_manager.get_supported_sample_rates()
        current_sample_rate = device_manager.get_sample_rate()
        bit_depths = device_manager.get_supported_bit_depths()
        current_bit_depth = device_manager.get_bit_depth()

        return cls(
            device_names=device_names,
            device_indices=device_indices,
            current_device_index=current_device_index,
            current_device_name=current_device_name,
            sample_rates=sample_rates,
            current_sample_rate=current_sample_rate,
            bit_depths=bit_depths,
            current_bit_depth=current_bit_depth,
        )
