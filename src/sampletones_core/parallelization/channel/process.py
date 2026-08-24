import multiprocessing
import queue
import threading
from multiprocessing.managers import SyncManager
from typing import Final, Optional

from sampletones_core.parallelization.channel.protocol import StepReporter
from sampletones_core.parallelization.task import TaskReport, TaskStep

SPAWN_CONTEXT: Final[str] = "spawn"


class QueueStepReporter:
    """The line one task reports on, made of a queue up and a flag down.

    Both ends are manager proxies, so the pair travels to a worker with the task it belongs to and
    reconnects there over the manager's own socket. That is what lets a worker started as a fresh
    interpreter — which is how every platform this runs on starts one — reach the run that sent it.
    """

    def __init__(
        self,
        reports: "queue.Queue[TaskReport]",
        withdrawn: threading.Event,
        index: int,
    ) -> None:
        self._reports = reports
        self._withdrawn = withdrawn
        self._index = index

    def __call__(self, step: TaskStep) -> bool:
        """Files the step under the task this line belongs to, and answers whether the run goes on.

        Args:
            step: Where the task now stands.

        Returns:
            bool: Whether the run still wants the answer this task is building.
        """
        self._reports.put(TaskReport(index=self._index, step=step))
        return not self._withdrawn.is_set()


class ProcessProgressChannel:
    """The line a run holds with tasks running in worker processes.

    A manager stands beside the pool and owns both ends, so each end reaches a task as an ordinary
    value the task is built with. The manager runs under the same spawn context the pool's workers
    do, which keeps one way of starting a process across the whole run.

    The channel is opened by the run that hands the lines out and closed by it once every task has
    been heard from, since the manager is a process of its own to be reaped.
    """

    def __init__(self) -> None:
        self._manager: SyncManager = multiprocessing.get_context(SPAWN_CONTEXT).Manager()
        self._reports: "queue.Queue[TaskReport]" = self._manager.Queue()
        self._withdrawn: threading.Event = self._manager.Event()

    def reporter(self, index: int) -> StepReporter:
        """The line the task at ``index`` reports on, which travels to its worker with it."""
        return QueueStepReporter(self._reports, self._withdrawn, index)

    def poll(self, timeout: float) -> Optional[TaskReport]:
        """The next report a task filed, waiting up to ``timeout`` seconds for one to arrive."""
        try:
            return self._reports.get(timeout=timeout)
        except queue.Empty:
            return None

    def withdraw(self) -> None:
        """Tells every task the run has let go of the answer it was building."""
        self._withdrawn.set()

    def close(self) -> None:
        """Ends the channel and reaps the manager process that held its ends."""
        self._manager.shutdown()
