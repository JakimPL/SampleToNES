from __future__ import annotations

from typing import Dict

from pydantic import BaseModel

from sampletones_core.audio import AudioDevice, AudioDeviceManager, CurrentDevice
from sampletones_core.constants.audio import BufferSize


class AudioSettingsViewModel(BaseModel, frozen=True):
    devices: Dict[int, AudioDevice]
    current_device: CurrentDevice
    buffer_size: BufferSize

    @classmethod
    def from_device_manager(
        cls,
        audio_device_manager: AudioDeviceManager,
    ) -> AudioSettingsViewModel:
        return cls(
            devices=audio_device_manager.list_devices(),
            current_device=audio_device_manager.get_current_device(),
            buffer_size=audio_device_manager.buffer_size,
        )
