import threading
from typing import Final, List

from sampletones_application.utils.midi.backends import MidiInputBackend

WAIT_SECONDS: Final[float] = 5.0


class RecordingSink:
    """A sink that keeps what a backend hands it, and the thread each call came from."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self.messages: List[bytes] = []
        self.losses: int = 0
        self.threads: List[str] = []

    def received(self, message: bytes) -> None:
        with self._condition:
            self.messages.append(message)
            self.threads.append(threading.current_thread().name)
            self._condition.notify_all()

    def lost(self) -> None:
        with self._condition:
            self.losses += 1
            self.threads.append(threading.current_thread().name)
            self._condition.notify_all()

    def wait_for_messages(self, count: int) -> List[bytes]:
        """The messages once at least ``count`` arrived, failing once ``WAIT_SECONDS`` pass first."""
        with self._condition:
            arrived = self._condition.wait_for(lambda: len(self.messages) >= count, timeout=WAIT_SECONDS)
            assert arrived, f"waited in vain for {count} messages, got {self.messages}"
            return list(self.messages)

    def wait_for_loss(self) -> None:
        with self._condition:
            assert self._condition.wait_for(lambda: self.losses > 0, timeout=WAIT_SECONDS), "the loss never came"


class ClosingSink(RecordingSink):
    """A sink that lets its backend go from inside the call handing it a message."""

    def __init__(self, backend: MidiInputBackend) -> None:
        super().__init__()
        self._backend = backend

    def received(self, message: bytes) -> None:
        self._backend.close()
        super().received(message)
