from dataclasses import dataclass
from typing import Dict, Optional
from unittest.mock import MagicMock

import pytest

from sampletones_application.view_model.shared.audio_settings import (
    BUFFER_SIZE_ITEMS,
    AudioDeviceItem,
    AudioSettingsViewModel,
    MasterGainReadout,
)
from sampletones_core.audio import AudioDevice, CurrentDevice
from sampletones_core.constants.audio import BUFFER_SIZES, BufferSize
from sampletones_shared.constants.audio import UNITY_GAIN

DEVICE_LABEL_FORMAT = "{index}: {name}"
SAMPLE_RATE_FORMAT = "{rate} Hz"
DECIBEL_FORMAT = "{decibels:+.1f} dB"
SILENT_LABEL = "-∞ dB"


def _device(index: int, name: str) -> AudioDevice:
    return AudioDevice(
        index=index,
        name=name,
        default_sample_rate=44100,
        supported_sample_rates=[22050, 44100, 48000],
        host_api=0,
    )


def _view_model(
    devices: Dict[int, AudioDevice],
    current_device: CurrentDevice,
    buffer_size: BufferSize,
    master_gain: float = UNITY_GAIN,
) -> AudioSettingsViewModel:
    audio_device_manager = MagicMock()
    audio_device_manager.list_devices.return_value = devices
    audio_device_manager.get_current_device.return_value = current_device
    audio_device_manager.buffer_size = buffer_size
    return AudioSettingsViewModel.from_device_manager(audio_device_manager, master_gain=master_gain)


@dataclass(frozen=True, kw_only=True)
class MappingCase:
    label: str
    devices: Dict[int, AudioDevice]
    current_device: CurrentDevice
    buffer_size: BufferSize
    current_device_label: str


MAPPING_CASES = [
    MappingCase(
        label="single_device",
        devices={0: _device(0, "Speakers")},
        current_device=CurrentDevice(device_index=0, name="Speakers", sample_rate=44100, host_api=0),
        buffer_size=1024,
        current_device_label="0: Speakers",
    ),
    MappingCase(
        label="multiple_devices",
        devices={0: _device(0, "Speakers"), 3: _device(3, "Headphones")},
        current_device=CurrentDevice(device_index=3, name="Headphones", sample_rate=48000, host_api=0),
        buffer_size=256,
        current_device_label="3: Headphones",
    ),
    MappingCase(
        label="no_devices",
        devices={},
        current_device=CurrentDevice.default(),
        buffer_size=512,
        current_device_label="",
    ),
]


class TestFromDeviceManager:
    """The projection carries display labels alongside the typed values a selection commits, so
    the window renders and resolves selections without formatting or parsing of its own.
    """

    @pytest.mark.parametrize("case", MAPPING_CASES, ids=lambda case: case.label)
    def test_projects_the_manager_state(self, case: MappingCase) -> None:
        view_model = _view_model(case.devices, case.current_device, case.buffer_size)

        assert view_model.devices == tuple(AudioDeviceItem.from_device(device) for device in case.devices.values())
        assert view_model.current_device_index == case.current_device.device_index
        assert view_model.current_sample_rate == case.current_device.sample_rate
        assert view_model.buffer_size == case.buffer_size

    def test_carries_the_master_gain(self) -> None:
        view_model = _view_model(
            {0: _device(0, "Speakers")},
            MAPPING_CASES[0].current_device,
            512,
            master_gain=1.5,
        )

        assert view_model.master_gain == 1.5

    @pytest.mark.parametrize("case", MAPPING_CASES, ids=lambda case: case.label)
    def test_current_device_label_matches_the_projected_item(self, case: MappingCase) -> None:
        view_model = _view_model(case.devices, case.current_device, case.buffer_size)

        assert view_model.current_device_label(DEVICE_LABEL_FORMAT) == case.current_device_label
        assert view_model.device_labels(DEVICE_LABEL_FORMAT) == [
            device.label(DEVICE_LABEL_FORMAT) for device in view_model.devices
        ]


class TestAudioDeviceItem:
    """The item absorbs the ``AudioDevice.index`` vs ``CurrentDevice.device_index`` field
    asymmetry and pairs every rendered label with the typed value it stands for."""

    def test_from_device_projects_the_core_fields(self) -> None:
        item = AudioDeviceItem.from_device(_device(3, "Headphones"))

        assert item.device_index == 3
        assert item.name == "Headphones"
        assert item.sample_rates == (22050, 44100, 48000)
        assert item.default_sample_rate == 44100

    def test_labels_pair_with_their_values(self) -> None:
        item = AudioDeviceItem.from_device(_device(3, "Headphones"))

        assert item.label(DEVICE_LABEL_FORMAT) == "3: Headphones"
        assert item.sample_rate_labels(SAMPLE_RATE_FORMAT) == (
            "22050 Hz",
            "44100 Hz",
            "48000 Hz",
        )
        assert item.default_sample_rate_label(SAMPLE_RATE_FORMAT) == "44100 Hz"


@dataclass(frozen=True, kw_only=True)
class CurrentDeviceCase:
    label: str
    current_device_index: int
    expected_index: Optional[int]


CURRENT_DEVICE_CASES = [
    CurrentDeviceCase(label="present", current_device_index=3, expected_index=3),
    CurrentDeviceCase(label="absent", current_device_index=7, expected_index=None),
]


class TestCurrentDevice:
    """The current device resolves against the projected list, reading as absent when the
    manager's device left the list (e.g. after unplugging)."""

    @pytest.mark.parametrize("case", CURRENT_DEVICE_CASES, ids=lambda case: case.label)
    def test_current_device_resolves_by_index(self, case: CurrentDeviceCase) -> None:
        devices = {0: _device(0, "Speakers"), 3: _device(3, "Headphones")}
        current_device = CurrentDevice(
            device_index=case.current_device_index,
            name="Headphones",
            sample_rate=48000,
            host_api=0,
        )
        view_model = _view_model(devices, current_device, 512)

        current_item = view_model.current_device
        if case.expected_index is None:
            assert current_item is None
            assert view_model.current_device_label(DEVICE_LABEL_FORMAT) == ""
        else:
            assert current_item is not None
            assert current_item.device_index == case.expected_index


class TestBufferSizeItems:
    """Every selectable buffer size pairs its combo label with the typed value it stands for."""

    def test_items_cover_the_supported_sizes(self) -> None:
        assert list(BUFFER_SIZE_ITEMS.values()) == list(BUFFER_SIZES)
        assert all(BUFFER_SIZE_ITEMS[str(size)] == size for size in BUFFER_SIZES)


@dataclass(frozen=True, kw_only=True)
class ReadoutCase:
    label: str
    gain: float
    db_label: str
    clip_fraction: float


READOUT_CASES = [
    ReadoutCase(label="silence", gain=0.0, db_label="-∞ dB", clip_fraction=0.0),
    ReadoutCase(label="attenuation", gain=0.5, db_label="-6.0 dB", clip_fraction=0.0),
    ReadoutCase(label="unity", gain=1.0, db_label="+0.0 dB", clip_fraction=0.0),
    ReadoutCase(label="boost", gain=1.5, db_label="+3.5 dB", clip_fraction=0.5),
    ReadoutCase(label="maximum", gain=2.0, db_label="+6.0 dB", clip_fraction=1.0),
]


class TestMasterGainReadout:
    """The readout projects a linear gain to the decibel label a slider shows and the boost
    fraction a warning gradient follows: ``0`` at unity or quieter, ramping to ``1`` at maximum.
    """

    @pytest.mark.parametrize("case", READOUT_CASES, ids=lambda case: case.label)
    def test_projects_the_gain(self, case: ReadoutCase) -> None:
        readout = MasterGainReadout.for_gain(case.gain, decibel_format=DECIBEL_FORMAT, silent_label=SILENT_LABEL)

        assert readout.db_label == case.db_label
        assert readout.clip_fraction == pytest.approx(case.clip_fraction)
