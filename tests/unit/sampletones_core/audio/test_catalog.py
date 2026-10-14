from typing import Final

import pytest

from sampletones_core.audio.catalog import DeviceCatalog
from sampletones_core.audio.device import CurrentDevice
from sampletones_core.constants.audio import SampleRate
from tests.suite.audio.machine import HEADPHONES, MICROPHONE, SPEAKERS, FakeDevice, ticking_machine

SPEAKERS_INDEX: Final[int] = 0
HEADPHONES_INDEX: Final[int] = 1
CHOSEN_RATE: Final[SampleRate] = 48000
UNPLAYED_RATE: Final[SampleRate] = 22050
SILENT_DEVICE: Final[FakeDevice] = FakeDevice(
    name="Silent",
    default_sample_rate=44100,
    supported_sample_rates=(),
    output_channels=2,
    host_api=0,
)


def _catalog(*devices: FakeDevice, default: int = SPEAKERS_INDEX) -> DeviceCatalog:
    return DeviceCatalog.read(ticking_machine(devices, default_device=default).driver())


def _current(device: FakeDevice, *, index: int, sample_rate: int) -> CurrentDevice:
    return CurrentDevice(device_index=index, name=device.name, sample_rate=sample_rate, host_api=device.host_api)


class TestReading:
    """A catalog lists every device that plays output at an offered rate, with the rates it plays."""

    def test_an_output_device_is_listed_with_the_rates_it_plays(self) -> None:
        catalog = _catalog(SPEAKERS)

        device = catalog.devices[SPEAKERS_INDEX]
        assert device.name == SPEAKERS.name
        assert tuple(device.supported_sample_rates) == SPEAKERS.supported_sample_rates

    def test_an_input_device_is_left_off(self) -> None:
        catalog = _catalog(MICROPHONE, SPEAKERS, default=1)

        assert [device.name for device in catalog.devices.values()] == [SPEAKERS.name]

    def test_a_device_playing_no_offered_rate_is_left_off(self) -> None:
        catalog = _catalog(SILENT_DEVICE, SPEAKERS, default=1)

        assert [device.name for device in catalog.devices.values()] == [SPEAKERS.name]


class TestDefault:
    """The system's default device stands at its default rate, and a machine naming none offers none."""

    def test_the_default_device_plays_at_its_default_rate(self) -> None:
        assert _catalog(SPEAKERS, HEADPHONES).default_device() == _current(
            SPEAKERS,
            index=SPEAKERS_INDEX,
            sample_rate=SPEAKERS.default_sample_rate,
        )

    def test_a_machine_with_no_device_offers_no_default(self) -> None:
        assert DeviceCatalog.read(ticking_machine((), default_device=None).driver()).default_device() is None


class TestChoosing:
    """A device plays at the rate chosen where it plays it, and at the first rate it offers otherwise."""

    def test_a_rate_the_device_plays_is_kept(self) -> None:
        assert _catalog(SPEAKERS).configured(SPEAKERS_INDEX, CHOSEN_RATE).sample_rate == CHOSEN_RATE

    def test_a_rate_the_device_refuses_falls_back_to_its_first(self) -> None:
        configured = _catalog(SPEAKERS).configured(SPEAKERS_INDEX, UNPLAYED_RATE)

        assert configured.sample_rate == SPEAKERS.supported_sample_rates[0]

    def test_an_unlisted_index_is_refused(self) -> None:
        with pytest.raises(ValueError):
            _catalog(SPEAKERS).configured(HEADPHONES_INDEX, CHOSEN_RATE)


class TestLocating:
    """A device chosen before a refresh is found again by its name, wherever the new backend lists it."""

    def test_a_device_moved_to_another_index_is_found_by_its_name(self) -> None:
        chosen = _current(HEADPHONES, index=HEADPHONES_INDEX, sample_rate=HEADPHONES.default_sample_rate)

        located = _catalog(HEADPHONES, SPEAKERS, default=1).locate(chosen)

        assert located == _current(HEADPHONES, index=0, sample_rate=HEADPHONES.default_sample_rate)

    def test_a_device_taken_off_the_list_is_found_nowhere(self) -> None:
        chosen = _current(HEADPHONES, index=HEADPHONES_INDEX, sample_rate=HEADPHONES.default_sample_rate)

        assert _catalog(SPEAKERS).locate(chosen) is None
