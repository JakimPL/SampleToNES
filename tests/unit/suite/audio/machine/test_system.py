from typing import Final

import pytest

from tests.suite.audio.machine import (
    DEVICE_BUSY,
    INVALID_DEVICE,
    FakeAudioSystem,
    OpenCall,
)
from tests.suite.audio.timeline import Opened, Refused, ViolationKind

BLOCK: Final[int] = 32


class TestExclusiveDevice:
    """The device plays one stream at a time, as a hardware device does."""

    def test_a_second_open_is_refused_as_busy_and_recorded(self, system: FakeAudioSystem) -> None:
        driver = system.driver()
        driver.open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)

        with pytest.raises(OSError, match=DEVICE_BUSY):
            driver.open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)

        assert system.timeline.violations() == [ViolationKind.OVERLAPPING_OPEN]
        assert system.timeline.most_streams_open() == 1

    def test_a_stream_opens_again_once_the_first_has_closed(self, system: FakeAudioSystem) -> None:
        driver = system.driver()
        driver.open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK).close()

        driver.open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)

        assert system.timeline.violations() == []
        assert len(system.timeline.of(Opened)) == 2

    def test_a_device_another_program_holds_refuses_without_a_violation(self, system: FakeAudioSystem) -> None:
        system.occupy()

        with pytest.raises(OSError, match=DEVICE_BUSY):
            system.driver().open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)

        assert system.timeline.violations() == []
        assert [refusal.reason for refusal in system.timeline.of(Refused)] == [DEVICE_BUSY]

    def test_a_device_let_go_of_opens_again(self, system: FakeAudioSystem) -> None:
        system.occupy()
        system.free()

        system.driver().open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)

        assert len(system.timeline.of(Opened)) == 1

    def test_a_device_the_driver_never_listed_is_refused(self, system: FakeAudioSystem) -> None:
        with pytest.raises(OSError, match=INVALID_DEVICE):
            system.driver().open_output(device_index=7, sample_rate=44100, frames_per_buffer=BLOCK)

        assert system.timeline.of(Opened) == []


class TestOpenHook:
    """An open hook runs on the opening thread before the device answers, so a case fails or holds the open."""

    def test_an_open_hook_raising_refuses_the_stream(self, system: FakeAudioSystem) -> None:
        def refuse(_call: OpenCall) -> None:
            raise OSError("the device is busy")

        system.hooks.before_open = refuse

        with pytest.raises(OSError, match="the device is busy"):
            system.driver().open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)

        assert system.timeline.of(Opened) == []
