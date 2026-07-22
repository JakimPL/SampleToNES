from __future__ import annotations

import math
from typing import Dict, Final, List, Optional, Tuple

from pydantic import BaseModel

from sampletones_core.audio import AudioDevice, AudioDeviceManager, amplitude_to_decibels
from sampletones_core.constants.audio import BUFFER_SIZES, BufferSize, SampleRate
from sampletones_shared.constants.audio import MAX_MASTER_GAIN, UNITY_GAIN
from sampletones_shared.utils.arrays import clamp

BUFFER_SIZE_ITEMS: Final[Dict[str, BufferSize]] = {str(size): size for size in BUFFER_SIZES}


def format_sample_rate(sample_rate: SampleRate, sample_rate_format: str) -> str:
    return sample_rate_format.format(rate=sample_rate)


class MasterGainReadout(BaseModel, frozen=True):
    """The decibel readout a master-gain slider projects: the label to display and the boost
    fraction it drives, ``0`` at unity or quieter and ``1`` at maximum gain, along which a warning
    gradient runs. The panel supplies the ``LanguageManager``-resolved decibel and silent labels."""

    db_label: str
    clip_fraction: float

    @classmethod
    def for_gain(cls, gain: float, *, decibel_format: str, silent_label: str) -> MasterGainReadout:
        decibels = amplitude_to_decibels(gain)
        db_label = silent_label if math.isinf(decibels) else decibel_format.format(decibels=decibels)
        clip_fraction = clamp((gain - UNITY_GAIN) / (MAX_MASTER_GAIN - UNITY_GAIN), 0.0, 1.0)
        return cls(db_label=db_label, clip_fraction=clip_fraction)


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

    def label(self, device_label_format: str) -> str:
        return device_label_format.format(index=self.device_index, name=self.name)

    def sample_rate_labels(self, sample_rate_format: str) -> Tuple[str, ...]:
        return tuple(format_sample_rate(sample_rate, sample_rate_format) for sample_rate in self.sample_rates)

    def default_sample_rate_label(self, sample_rate_format: str) -> str:
        return format_sample_rate(self.default_sample_rate, sample_rate_format)


class AudioSettingsViewModel(BaseModel, frozen=True):
    devices: Tuple[AudioDeviceItem, ...]
    current_device_index: int
    current_sample_rate: SampleRate
    buffer_size: BufferSize
    master_gain: float

    @classmethod
    def from_device_manager(
        cls,
        audio_device_manager: AudioDeviceManager,
        *,
        master_gain: float,
    ) -> AudioSettingsViewModel:
        current_device = audio_device_manager.get_current_device()
        return cls(
            devices=tuple(
                AudioDeviceItem.from_device(device) for device in audio_device_manager.list_devices().values()
            ),
            current_device_index=current_device.device_index,
            current_sample_rate=current_device.sample_rate,
            buffer_size=audio_device_manager.buffer_size,
            master_gain=master_gain,
        )

    def device_labels(self, device_label_format: str) -> List[str]:
        return [device.label(device_label_format) for device in self.devices]

    def current_device_label(self, device_label_format: str) -> str:
        """The label of the device the manager currently drives, empty when it left the list."""
        current_device = self.current_device
        return current_device.label(device_label_format) if current_device is not None else ""

    @property
    def current_device(self) -> Optional[AudioDeviceItem]:
        for device in self.devices:
            if device.device_index == self.current_device_index:
                return device

        return None

    def current_sample_rate_label(self, sample_rate_format: str) -> str:
        return format_sample_rate(self.current_sample_rate, sample_rate_format)

    @property
    def buffer_size_label(self) -> str:
        return str(self.buffer_size)
