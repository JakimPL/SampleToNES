import threading
from collections import deque
from typing import Deque

from sampletones_shared.types.callback import VoidCallback


class QueuedPost:
    """The owner's thread as a queue a case drains, the way the render thread drains the callback queue.

    A report waits here until the case drains it on its own thread, so a case can hold reports back and let a
    request overtake them.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._deliveries: Deque[VoidCallback] = deque()

    def __call__(self, delivery: VoidCallback) -> None:
        with self._lock:
            self._deliveries.append(delivery)

    @property
    def waiting(self) -> int:
        with self._lock:
            return len(self._deliveries)

    def drain(self) -> None:
        """Runs every delivery waiting, in the order it was posted, those posted meanwhile included."""
        while True:
            with self._lock:
                if not self._deliveries:
                    return

                delivery = self._deliveries.popleft()

            delivery()
