from dataclasses import dataclass
from typing import Dict
from unittest.mock import MagicMock

import pytest

from sampletones_application.view_model.shared.audio_settings import AudioSettingsViewModel
from sampletones_core.audio import AudioDevice, CurrentDevice
from sampletones_core.constants.audio import BufferSize


def _device(index: int, name: str) -> AudioDevice:
    return AudioDevice(
        index=index,
        name=name,
        is_input=False,
        is_output=True,
        is_default_input=False,
        is_default_output=index == 0,
        default_sample_rate=44100,
        supported_sample_rates=[22050, 44100, 48000],
        host_api=0,
    )


@dataclass(frozen=True, kw_only=True)
class MappingCase:
    label: str
    devices: Dict[int, AudioDevice]
    current_device: CurrentDevice
    buffer_size: BufferSize


MAPPING_CASES = [
    MappingCase(
        label="single_device",
        devices={0: _device(0, "Speakers")},
        current_device=CurrentDevice(device_index=0, name="Speakers", sample_rate=44100, host_api=0),
        buffer_size=1024,
    ),
    MappingCase(
        label="multiple_devices",
        devices={0: _device(0, "Speakers"), 3: _device(3, "Headphones")},
        current_device=CurrentDevice(device_index=3, name="Headphones", sample_rate=48000, host_api=0),
        buffer_size=256,
    ),
    MappingCase(
        label="no_devices",
        devices={},
        current_device=CurrentDevice.default(),
        buffer_size=512,
    ),
]


class TestFromDeviceManager:
    @pytest.mark.parametrize("case", MAPPING_CASES, ids=lambda case: case.label)
    def test_snapshots_the_manager_state(self, case: MappingCase) -> None:
        audio_device_manager = MagicMock()
        audio_device_manager.list_devices.return_value = case.devices
        audio_device_manager.get_current_device.return_value = case.current_device
        audio_device_manager.buffer_size = case.buffer_size

        view_model = AudioSettingsViewModel.from_device_manager(audio_device_manager)

        assert view_model.devices == case.devices
        assert view_model.current_device == case.current_device
        assert view_model.buffer_size == case.buffer_size
