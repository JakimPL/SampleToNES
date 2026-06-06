from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, ConfigDict

from sampletones_core.audio import (
    AudioDevice,
    AudioDeviceManager,
    CurrentDevice,
)


class AudioSettingsData(BaseModel):
    model_config = ConfigDict(frozen=True)

    devices: Dict[int, AudioDevice]
    current_device: CurrentDevice

    @classmethod
    def from_device_manager(cls, audio_device_manager: AudioDeviceManager) -> AudioSettingsData:
        output_devices = audio_device_manager.list_devices()
        current_device = audio_device_manager.get_current_device()

        return cls(
            devices=output_devices,
            current_device=current_device,
        )
