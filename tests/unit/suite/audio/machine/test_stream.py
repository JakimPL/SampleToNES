from typing import Final, List

import numpy as np
import pytest

from tests.suite.audio.machine import (
    STREAM_CLOSED,
    FakeAudioSystem,
    StreamCall,
)
from tests.suite.audio.ramp import ramp, ramp_indices
from tests.suite.audio.timeline import Closed, ViolationKind

BLOCK: Final[int] = 32
CLOSE_FAILED: Final[str] = "Close failed"


def _failing_close(_call: StreamCall) -> None:
    raise OSError(CLOSE_FAILED)


class TestStreamUse:
    """The timeline holds what each stream played, and every use of a stream a correct playback never makes."""

    def test_what_a_stream_plays_reads_back_as_its_document_indices(self, system: FakeAudioSystem) -> None:
        stream = system.driver().open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)
        for index in range(3):
            stream.write(ramp(BLOCK, start=index * BLOCK).tobytes())

        np.testing.assert_array_equal(ramp_indices(system.timeline.written(stream.stream)), np.arange(3 * BLOCK))

    def test_a_write_after_a_close_fails_and_is_recorded(self, system: FakeAudioSystem) -> None:
        stream = system.driver().open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)
        stream.close()

        with pytest.raises(OSError, match=STREAM_CLOSED):
            stream.write(ramp(BLOCK).tobytes())

        assert system.timeline.violations() == [ViolationKind.WRITE_AFTER_CLOSE]

    def test_a_drain_after_a_close_fails_and_is_recorded(self, system: FakeAudioSystem) -> None:
        stream = system.driver().open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)
        stream.close()

        with pytest.raises(OSError, match=STREAM_CLOSED):
            stream.drain()

        assert system.timeline.violations() == [ViolationKind.DRAIN_AFTER_CLOSE]

    def test_a_second_close_is_recorded(self, system: FakeAudioSystem) -> None:
        stream = system.driver().open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)
        stream.close()

        stream.close()

        assert system.timeline.violations() == [ViolationKind.CLOSE_TWICE]
        assert len(system.timeline.of(Closed)) == 1

    def test_a_drained_and_closed_stream_leaves_nothing_open(self, system: FakeAudioSystem) -> None:
        stream = system.driver().open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)
        stream.write(ramp(BLOCK).tobytes())

        stream.drain()
        stream.close()

        assert system.timeline.open_streams() == set()
        assert system.timeline.violations() == []


class TestStreamHooks:
    """A stream hook runs on the writing thread before each call, so a case fails, holds or races it there."""

    def test_a_write_hook_sees_how_many_writes_came_before(self, system: FakeAudioSystem) -> None:
        seen: List[int] = []
        system.hooks.before_write = lambda call: seen.append(call.writes)
        stream = system.driver().open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)

        for index in range(3):
            stream.write(ramp(BLOCK, start=index * BLOCK).tobytes())

        assert seen == [0, 1, 2]

    def test_a_write_hook_raising_fails_that_write_alone(self, system: FakeAudioSystem) -> None:
        def fail_the_second(call: StreamCall) -> None:
            if call.writes == 1:
                raise OSError("the device went away")

        system.hooks.before_write = fail_the_second
        stream = system.driver().open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)
        stream.write(ramp(BLOCK).tobytes())

        with pytest.raises(OSError, match="the device went away"):
            stream.write(ramp(BLOCK, start=BLOCK).tobytes())

        np.testing.assert_array_equal(ramp_indices(system.timeline.written()), np.arange(BLOCK))

    def test_a_close_hook_runs_before_the_stream_closes(self, system: FakeAudioSystem) -> None:
        open_when_hooked: List[bool] = []
        system.hooks.before_close = lambda call: open_when_hooked.append(call.stream in system.timeline.open_streams())
        stream = system.driver().open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)

        stream.close()

        assert open_when_hooked == [True]

    def test_a_close_that_fails_lets_the_device_go(self, system: FakeAudioSystem) -> None:
        system.hooks.before_close = _failing_close
        stream = system.driver().open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)

        with pytest.raises(OSError, match=CLOSE_FAILED):
            stream.close()

        system.hooks.before_close = None
        system.driver().open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK).close()
        assert not system.timeline.open_streams()
        assert not system.timeline.violations()
