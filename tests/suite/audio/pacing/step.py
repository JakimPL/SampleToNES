import threading
from typing import Dict


class StepPacing:
    """A device that takes each write only when the case lets it, so a case decides every interleaving.

    A grant lets one write through. A writer finding no grant waits inside its write until the case gives
    one, and the case can wait in turn until a writer stands there. A drain returns at once, since every
    write granted has been played.
    """

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._granted: int = 0
        self._admitted: int = 0
        self._waiting: int = 0
        self._discarded: Dict[int, bool] = {}

    @property
    def admitted(self) -> int:
        """How many writes the device has taken."""
        with self._condition:
            return self._admitted

    def grant(self, writes: int) -> None:
        """Lets ``writes`` more writes through, whichever streams they come from."""
        with self._condition:
            self._granted += writes
            self._condition.notify_all()

    def wait_for_writer(self, *, timeout: float) -> bool:
        """Waits until a writer stands inside a write for want of a grant, and reports whether one arrived in time."""
        with self._condition:
            return self._condition.wait_for(lambda: self._waiting > 0, timeout=timeout)

    def admit(self, stream: int, frames: int, sample_rate: int) -> None:
        with self._condition:
            if self._granted == 0 and not self._discarded.get(stream, False):
                self._waiting += 1
                self._condition.notify_all()
                try:
                    self._condition.wait_for(lambda: self._granted > 0 or self._discarded.get(stream, False))
                finally:
                    self._waiting -= 1

            if self._discarded.get(stream, False):
                return

            self._granted -= 1
            self._admitted += 1

    def drain(self, stream: int) -> None:
        return None

    def discard(self, stream: int) -> int:
        with self._condition:
            self._discarded[stream] = True
            self._condition.notify_all()

        return 0
