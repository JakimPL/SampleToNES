import threading
from typing import Final

from sampletones_core.audio.output import AudioThreads

WAIT_SECONDS: Final[float] = 10.0
SHORT_DEADLINE: Final[float] = 0.05
WORKER: Final[str] = "AudioThreadsCase"


class TestJoin:
    """A teardown waits for every thread the registry started, and answers each one that outlives its deadline."""

    def test_every_thread_that_ended_is_waited_for(self) -> None:
        threads = AudioThreads()
        threads.start(lambda: None, name=WORKER)

        assert threads.join(deadline_seconds=WAIT_SECONDS) == []

    def test_a_thread_outliving_the_deadline_is_answered(self) -> None:
        threads = AudioThreads()
        release = threading.Event()
        held = threads.start(lambda: release.wait(timeout=WAIT_SECONDS), name=WORKER)

        survivors = threads.join(deadline_seconds=SHORT_DEADLINE)
        release.set()
        held.join(timeout=WAIT_SECONDS)

        assert survivors == [held]

    def test_a_thread_is_started_before_it_can_be_waited_for(self) -> None:
        threads = AudioThreads()
        started = threads.start(lambda: None, name=WORKER)

        assert started.ident is not None
        assert started.daemon
