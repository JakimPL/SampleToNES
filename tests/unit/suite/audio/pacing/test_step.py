import threading
from typing import Callable, Final, List

from tests.suite.audio.machine import SPEAKERS, STREAM_CLOSED, stepped_machine
from tests.suite.audio.pacing import StepPacing
from tests.suite.audio.ramp import ramp
from tests.suite.audio.timeline import Written

WAIT_SECONDS: Final[float] = 5.0
BLOCK: Final[int] = 64


def _writer(stream_write: Callable[[bytes], None], blocks: int, failures: List[OSError]) -> threading.Thread:
    def write() -> None:
        try:
            for index in range(blocks):
                stream_write(ramp(BLOCK, start=index * BLOCK).tobytes())
        except OSError as error:
            failures.append(error)

    thread = threading.Thread(target=write, daemon=True, name="CaseWriter")
    thread.start()
    return thread


class TestStepPacing:
    """A stepped device takes each write only when the case grants it, so a case holds every interleaving."""

    def test_a_write_waits_until_it_is_granted(self) -> None:
        system = stepped_machine([SPEAKERS], default_device=0)
        pacing = system.pacing
        assert isinstance(pacing, StepPacing)
        stream = system.driver().open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)
        failures: List[OSError] = []
        writer = _writer(stream.write, 1, failures)

        assert pacing.wait_for_writer(timeout=WAIT_SECONDS)
        assert writer.is_alive()
        assert system.timeline.of(Written) == []

        pacing.grant(1)
        writer.join(timeout=WAIT_SECONDS)

        assert not writer.is_alive()
        assert len(system.timeline.of(Written)) == 1
        assert failures == []

    def test_a_grant_lets_that_many_writes_through(self) -> None:
        system = stepped_machine([SPEAKERS], default_device=0)
        pacing = system.pacing
        assert isinstance(pacing, StepPacing)
        stream = system.driver().open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)
        failures: List[OSError] = []
        pacing.grant(2)
        writer = _writer(stream.write, 3, failures)

        assert pacing.wait_for_writer(timeout=WAIT_SECONDS)

        assert writer.is_alive()
        assert pacing.admitted == 2
        assert len(system.timeline.of(Written)) == 2

        pacing.grant(1)
        writer.join(timeout=WAIT_SECONDS)
        assert len(system.timeline.of(Written)) == 3

    def test_a_close_from_another_thread_wakes_the_waiting_writer_with_a_failure(self) -> None:
        system = stepped_machine([SPEAKERS], default_device=0)
        pacing = system.pacing
        assert isinstance(pacing, StepPacing)
        stream = system.driver().open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)
        failures: List[OSError] = []
        writer = _writer(stream.write, 1, failures)
        assert pacing.wait_for_writer(timeout=WAIT_SECONDS)

        stream.close()
        writer.join(timeout=WAIT_SECONDS)

        assert not writer.is_alive()
        assert [str(failure) for failure in failures] == [STREAM_CLOSED]
        assert system.timeline.of(Written) == []
