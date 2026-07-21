import threading
from typing import Optional

from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_shared.types.callback import VoidCallback


class LatestWinsExecutor:
    """Runs tasks on a single background thread, keeping only the latest queued task.

    While a task runs, submitting another replaces any task still waiting, so a burst of
    rapid submissions collapses to one trailing run — the latest wins, and that final
    submission always runs. The worker drains to the newest pending task before it stops,
    and ``wait=True`` on the next launch joins a worker still tearing down, so a submission
    made during that hand-off carries into the next run. Built on :class:`SingleThreadExecutor`,
    so its worker joins at teardown like any other background thread.

    ``is_running`` reports the busy span as a single truth: true from the first submission
    until the worker drains every queued task and stops. Callers read this single span to
    drive activity indication or exclusion.
    """

    def __init__(self) -> None:
        self._executor = SingleThreadExecutor()
        self._lock = threading.Lock()
        self._pending: Optional[VoidCallback] = None
        self._running: bool = False

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def submit(self, task: VoidCallback) -> bool:
        """Queues ``task`` as the latest work, launching the worker when the queue is idle.

        Returns whether the queue is being served: a task accepted into a running or freshly
        launched queue returns ``True``; ``False`` reports that the worker failed to launch,
        which a caller may surface.
        """
        with self._lock:
            self._pending = task
            if self._running:
                return True

            self._running = True

        launched = self._executor.execute(self._drain, wait=True)
        if not launched:
            with self._lock:
                self._running = False

        return launched

    def _drain(self) -> None:
        """Runs queued tasks to exhaustion, always taking the newest pending one.

        Between tasks the worker pops the latest submission under the lock, so a burst
        collapses to a single trailing run. It clears the running flag and exits only once
        no task remains, so every submission is picked up by the running worker or launches
        a fresh one.
        """
        while True:
            with self._lock:
                task = self._pending
                self._pending = None
                if task is None:
                    self._running = False
                    return

            task()
