import threading
from typing import Dict, Set, Tuple

from sampletones_core.parallelization.task import TaskReport, TaskStep


class TaskSteps:
    """Where each running task of a run stands, as the tasks themselves last said.

    A task reports from wherever it runs while the run's monitor waits on the results the pool
    hands back, so the two arrive on different threads and meet here. An entry lives from a task's
    first report until the run counts that task as finished, which is what keeps a task's own
    progress and the run's completed count from describing the same work twice.

    A finished task stays finished. Its reports travel a line the run reads at its own pace, so one
    filed before the result arrived may be read after it; the run has already counted that task
    whole, and what it said on the way there is history by then.
    """

    def __init__(self) -> None:
        self._steps: Dict[int, TaskStep] = {}
        self._finished: Set[int] = set()
        self._lock = threading.Lock()

    def record(self, report: TaskReport) -> None:
        """Takes the step a task filed as where that task now stands, while it is still running."""
        with self._lock:
            if report.index in self._finished:
                return

            self._steps[report.index] = report.step

    def complete(self, index: int) -> None:
        """Counts the task at ``index`` among the finished, whose work the run now carries itself."""
        with self._lock:
            self._finished.add(index)
            self._steps.pop(index, None)

    def clear(self) -> None:
        """Lets go of every task, which is where a run about to start over stands."""
        with self._lock:
            self._steps.clear()
            self._finished.clear()

    def snapshot(self) -> Tuple[TaskStep, ...]:
        """Where the running tasks stand, in the order the run handed them out."""
        with self._lock:
            return tuple(self._steps[index] for index in sorted(self._steps))
