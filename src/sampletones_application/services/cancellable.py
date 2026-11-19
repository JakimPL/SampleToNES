import threading
from functools import partial
from typing import Final, TypeVar

from sampletones_application.services.base import ServiceBase
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback

ResultT = TypeVar("ResultT")
DEFAULT_PRIORITY: Final[int] = 0


class CancellableJobService(ServiceBase[ResultT]):
    """A service running one job at a time on a worker of its own, which a cancel asks to stop.

    A job reads the cancel at the points it looks up, and a request arriving while a job runs is
    declined, so the running flag stands from the moment a job is taken until it ends whichever
    way it ends.
    """

    def __init__(self, priority: int = DEFAULT_PRIORITY) -> None:
        super().__init__(priority)
        self._executor = SingleThreadExecutor()
        self._cancel_event = threading.Event()
        self._running = threading.Event()

    def cancel(self) -> None:
        """Asks the running job to stop at the next point it looks up."""
        self._cancel_event.set()

    def is_running(self) -> bool:
        return self._running.is_set()

    def shutdown(self) -> None:
        """Winds a running job down for application exit.

        The worker runs on a :class:`SingleThreadExecutor`, so the teardown that joins every
        background worker reaches this one; asking it to stop first is what keeps that join short.
        """
        self._cancel_event.set()

    def _start_job(self, job: VoidCallback) -> bool:
        """Runs ``job`` on the worker where no job is running; reports whether it took the request."""
        if self.is_running():
            logger.warning(f"{self.class_name}: a job is already running; the request was declined")
            return False

        self._cancel_event.clear()
        self._running.set()
        if not self._executor.execute(partial(self._run_to_its_end, job), wait=False):
            self._running.clear()
            return False

        return True

    def _run_to_its_end(self, job: VoidCallback) -> None:
        try:
            job()
        finally:
            self._running.clear()
