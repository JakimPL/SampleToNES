from typing import Final

import pytest

from tests.suite.audio.machine import (
    BACKEND_TERMINATED,
    HEADPHONES,
    MICROPHONE,
    SPEAKERS,
    FakeAudioSystem,
    ticking_machine,
)
from tests.suite.audio.timeline import Terminated, ViolationKind

BLOCK: Final[int] = 32


class TestDeviceList:
    """A driver lists the machine's devices as they stood when it was created, inputs included."""

    def test_every_device_is_listed_with_what_it_plays(self, system: FakeAudioSystem) -> None:
        driver = system.driver()

        listed = [driver.device(index) for index in range(driver.device_count())]

        assert [device.name for device in listed] == [SPEAKERS.name, HEADPHONES.name, MICROPHONE.name]
        assert [device.plays_output for device in listed] == [True, True, False]

    def test_a_rate_the_device_plays_is_supported_and_another_is_not(self, system: FakeAudioSystem) -> None:
        driver = system.driver()

        assert driver.supports(1, 96000) is True
        assert driver.supports(0, 96000) is False

    def test_the_default_device_is_the_one_the_machine_names(self, system: FakeAudioSystem) -> None:
        assert system.driver().default_output_index() == 0

    def test_a_machine_naming_no_default_answers_none(self) -> None:
        system = ticking_machine([MICROPHONE], default_device=None)

        assert system.driver().default_output_index() is None

    def test_a_driver_keeps_the_list_it_was_created_with(self, system: FakeAudioSystem) -> None:
        before = system.driver()

        system.devices = [HEADPHONES]
        after = system.driver()

        assert before.device_count() == 3
        assert after.device_count() == 1
        assert after.device(0).name == HEADPHONES.name


class TestBackendLifecycle:
    """A terminated backend answers nothing, and terminating it under an open stream is recorded."""

    def test_terminating_under_an_open_stream_is_recorded(self, system: FakeAudioSystem) -> None:
        driver = system.driver()
        driver.open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)

        driver.terminate()

        assert system.timeline.violations() == [ViolationKind.TERMINATE_WITH_OPEN_STREAM]

    def test_terminating_with_every_stream_closed_is_clean(self, system: FakeAudioSystem) -> None:
        driver = system.driver()
        driver.open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK).close()

        driver.terminate()

        assert system.timeline.violations() == []
        assert len(system.timeline.of(Terminated)) == 1

    def test_a_call_after_termination_fails_and_is_recorded(self, system: FakeAudioSystem) -> None:
        driver = system.driver()
        driver.terminate()

        with pytest.raises(OSError, match=BACKEND_TERMINATED):
            driver.device_count()

        assert system.timeline.violations() == [ViolationKind.USE_AFTER_TERMINATE]
