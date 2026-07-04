from __future__ import annotations

from typing import Dict, Final, List, Optional, Tuple

from pydantic import BaseModel

from sampletones_core.audio import AudioDevice, AudioDeviceManager
from sampletones_core.constants.audio import BUFFER_SIZES, BufferSize, SampleRate

DEVICE_LABEL_FORMAT: Final[str] = "{index}: {name}"
SAMPLE_RATE_LABEL_FORMAT: Final[str] = "{rate} Hz"

BUFFER_SIZE_ITEMS: Final[Dict[str, BufferSize]] = {str(size): size for size in BUFFER_SIZES}


def format_sample_rate(sample_rate: SampleRate) -> str:
    return SAMPLE_RATE_LABEL_FORMAT.format(rate=sample_rate)


class AudioDeviceItem(BaseModel, frozen=True):
    """One selectable output device, projected for display: the labels the combos render and the
    typed values a selection commits."""

    device_index: int
    name: str
    sample_rates: Tuple[SampleRate, ...]
    default_sample_rate: SampleRate

    @classmethod
    def from_device(cls, device: AudioDevice) -> AudioDeviceItem:
        return cls(
            device_index=device.index,
            name=device.name,
            sample_rates=tuple(device.supported_sample_rates),
            default_sample_rate=device.default_sample_rate,
        )

    @property
    def label(self) -> str:
        return DEVICE_LABEL_FORMAT.format(index=self.device_index, name=self.name)

    @property
    def sample_rate_labels(self) -> Tuple[str, ...]:
        return tuple(format_sample_rate(sample_rate) for sample_rate in self.sample_rates)

    @property
    def default_sample_rate_label(self) -> str:
        return format_sample_rate(self.default_sample_rate)


class AudioSettingsViewModel(BaseModel, frozen=True):
    devices: Tuple[AudioDeviceItem, ...]
    current_device_index: int
    current_sample_rate: SampleRate
    buffer_size: BufferSize

    @classmethod
    def from_device_manager(
        cls,
        audio_device_manager: AudioDeviceManager,
    ) -> AudioSettingsViewModel:
        current_device = audio_device_manager.get_current_device()
        return cls(
            devices=tuple(
                AudioDeviceItem.from_device(device) for device in audio_device_manager.list_devices().values()
            ),
            current_device_index=current_device.device_index,
            current_sample_rate=current_device.sample_rate,
            buffer_size=audio_device_manager.buffer_size,
        )

    @property
    def device_labels(self) -> List[str]:
        return [device.label for device in self.devices]

    @property
    def current_device_label(self) -> str:
        """The label of the device the manager currently drives, empty when it left the list."""
        current_device = self.current_device
        return current_device.label if current_device is not None else ""

    @property
    def current_device(self) -> Optional[AudioDeviceItem]:
        for device in self.devices:
            if device.device_index == self.current_device_index:
                return device

        return None

    @property
    def current_sample_rate_label(self) -> str:
        return format_sample_rate(self.current_sample_rate)

    @property
    def buffer_size_label(self) -> str:
        return str(self.buffer_size)
