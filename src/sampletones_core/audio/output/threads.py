import threading
import time
from typing import List

from sampletones_shared.types.callback import VoidCallback


class AudioThreads:
    """Every thread the output's sound runs on, started here so a teardown can wait for each one.

    A thread starts under the registry's lock, so a teardown waiting meanwhile meets it started. Each one is
    a daemon, so a thread a device holds for good leaves the process free to exit.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._threads: List[threading.Thread] = []

    def start(self, target: VoidCallback, *, name: str) -> threading.Thread:
        """Starts ``target`` on a thread of its own, named ``name``."""
        thread = threading.Thread(target=target, name=name, daemon=True)
        with self._lock:
            self._threads = [kept for kept in self._threads if kept.is_alive()]
            self._threads.append(thread)
            thread.start()

        return thread

    def join(self, *, deadline_seconds: float) -> List[threading.Thread]:
        """Waits until every thread started here has ended or ``deadline_seconds`` have passed.

        Returns:
            List[threading.Thread]: The threads still running once the deadline passed.
        """
        deadline = time.monotonic() + deadline_seconds
        with self._lock:
            threads = list(self._threads)

        for thread in threads:
            thread.join(timeout=max(0.0, deadline - time.monotonic()))

        return [thread for thread in threads if thread.is_alive()]
