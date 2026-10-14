from typing import Final

import pytest

from sampletones_core.audio.catalog import DeviceCatalog
from sampletones_core.audio.device import CurrentDevice
from sampletones_core.audio.manager import AudioDeviceManager
from sampletones_core.constants.audio import DEFAULT_BUFFER_SIZE, BufferSize, SampleRate
from tests.suite.audio.machine import HEADPHONES, SPEAKERS, FakeDevice, ticking_machine

SPEAKERS_INDEX: Final[int] = 0
HEADPHONES_INDEX: Final[int] = 1
CHOSEN_RATE: Final[SampleRate] = 48000
CHOSEN_BUFFER: Final[BufferSize] = 256
UNOFFERED_BUFFER: Final[int] = 1000
UNPLUGGED: Final[str] = "Unplugged"


def _catalog(*devices: FakeDevice, default: int = SPEAKERS_INDEX) -> DeviceCatalog:
    return DeviceCatalog.read(ticking_machine(devices, default_device=default).driver())


@pytest.fixture(name="manager")
def manager_fixture() -> AudioDeviceManager:
    """A manager over a machine whose speakers are its default device, with headphones beside them."""
    return AudioDeviceManager(_catalog(SPEAKERS, HEADPHONES))


class TestCurrentDevice:
    """The device in force reads as ``None`` wherever nothing is chosen, and as the choice otherwise."""

    def test_the_default_device_is_in_force(self, manager: AudioDeviceManager) -> None:
        assert manager.get_current_device() == CurrentDevice(
            device_index=SPEAKERS_INDEX,
            name=SPEAKERS.name,
            sample_rate=SPEAKERS.default_sample_rate,
            host_api=SPEAKERS.host_api,
        )

    def test_a_machine_offering_no_device_has_none_in_force(self) -> None:
        manager = AudioDeviceManager(DeviceCatalog.read(ticking_machine((), default_device=None).driver()))

        assert manager.list_devices() == {}
        assert manager.get_current_device() is None
        assert manager.settings.device is None

    def test_configuring_answers_the_device_now_in_force(self, manager: AudioDeviceManager) -> None:
        configured = manager.configure_device(HEADPHONES_INDEX, CHOSEN_RATE)

        assert configured.name == HEADPHONES.name
        assert manager.get_current_device() == configured
        assert manager.settings.device == configured

    def test_configuring_an_unlisted_device_is_refused_and_keeps_the_choice(self, manager: AudioDeviceManager) -> None:
        before = manager.get_current_device()

        with pytest.raises(ValueError):
            manager.configure_device(len(manager.list_devices()), CHOSEN_RATE)

        assert manager.get_current_device() == before


class TestRefresh:
    """A refreshed catalog finds the device in force again by its name, and a device taken off leaves none."""

    def test_a_device_moved_to_another_index_stays_in_force(self, manager: AudioDeviceManager) -> None:
        manager.configure_device(HEADPHONES_INDEX, CHOSEN_RATE)

        manager.adopt(_catalog(HEADPHONES, SPEAKERS, default=1))

        current = manager.get_current_device()
        assert current is not None
        assert (current.name, current.device_index, current.sample_rate) == (HEADPHONES.name, 0, CHOSEN_RATE)

    def test_a_device_taken_off_the_list_leaves_none_in_force(self, manager: AudioDeviceManager) -> None:
        manager.adopt(_catalog(HEADPHONES, default=0))

        assert manager.get_current_device() is None
        assert [device.name for device in manager.list_devices().values()] == [HEADPHONES.name]


class TestSavedSession:
    """A saved device is found by its name, and a missing one falls back to the system's default."""

    def test_a_saved_device_is_found_by_its_name(self, manager: AudioDeviceManager) -> None:
        saved = CurrentDevice(device_index=7, name=HEADPHONES.name, sample_rate=CHOSEN_RATE, host_api=0)

        manager.set_current_device(saved)

        current = manager.get_current_device()
        assert current is not None
        assert (current.device_index, current.sample_rate) == (HEADPHONES_INDEX, CHOSEN_RATE)

    def test_a_missing_device_falls_back_to_the_default(self, manager: AudioDeviceManager) -> None:
        manager.configure_device(HEADPHONES_INDEX, CHOSEN_RATE)

        manager.set_current_device(CurrentDevice(device_index=0, name=UNPLUGGED, sample_rate=CHOSEN_RATE, host_api=0))

        current = manager.get_current_device()
        assert current is not None
        assert current.name == SPEAKERS.name


class TestBufferSize:
    """The buffer size is one the application offers, and it reaches the settings the output plays on."""

    def test_an_offered_buffer_size_is_taken(self, manager: AudioDeviceManager) -> None:
        manager.set_buffer_size(CHOSEN_BUFFER)

        assert manager.settings.buffer_size == CHOSEN_BUFFER

    def test_an_unoffered_buffer_size_is_refused(self, manager: AudioDeviceManager) -> None:
        with pytest.raises(ValueError):
            manager.set_buffer_size(UNOFFERED_BUFFER)

        assert manager.buffer_size == DEFAULT_BUFFER_SIZE
