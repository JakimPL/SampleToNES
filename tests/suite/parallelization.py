import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Final, FrozenSet, List, Optional, Tuple

from sampletones_core.parallelization.channel.protocol import StepReporter
from sampletones_core.parallelization.processor import TaskProcessor
from sampletones_core.parallelization.task import TaskProgress, TaskStatus, TaskStep
from sampletones_shared.exceptions import OperationCancelled
from tests.suite.release import wait_for_release

COUNTING_STAGE: Final[str] = "counting"
STEP_COUNT: Final[int] = 8
HALFWAY: Final[int] = STEP_COUNT // 2
NOTHING_COMPLETED: Final[int] = 0
WHOLE_TASK: Final[float] = 1.0
ONE_STEP: Final[int] = 1

LIVE_STATUSES: Final[FrozenSet[TaskStatus]] = frozenset({TaskStatus.RUNNING, TaskStatus.COMPLETED})


@dataclass(frozen=True)
class CountingTask:
    """One task of a run that counts, reports each count, and does nothing else.

    A reconstruction needs an audio file, an instruction library and seconds of arithmetic before
    it can say anything about itself, none of which the channel carrying what it says depends on.
    Counting stands in for the work, so what a test of the channel measures is the channel.

    The task waits at the halfway mark until the file at ``release_path`` appears, which is how a
    test can assert that a partial report arrived while the task was provably still running.
    """

    index: int
    report: StepReporter
    release_path: Path


def count_task(task: CountingTask) -> int:
    """Counts to ``STEP_COUNT``, reporting each count, and answers which task did the counting.

    Runs in a pool worker, so the line it reports on travelled here with it.

    Raises:
        OperationCancelled: If the run is withdrawn while the counting is under way.
    """
    for completed in range(1, STEP_COUNT + 1):
        step = TaskStep(
            stage=COUNTING_STAGE,
            completed=completed,
            total=STEP_COUNT,
            fraction=completed / STEP_COUNT,
        )
        if not task.report(step):
            raise OperationCancelled(f"task {task.index} was withdrawn at {completed}")

        if completed == HALFWAY:
            wait_for_release(task.release_path)

    return task.index


class CountingProcessor(TaskProcessor[int]):
    """A run whose tasks only count, so what a test reads is the channel they count over."""

    def __init__(self, task_count: int, release_path: Path, max_workers: int) -> None:
        super().__init__(max_workers=max_workers)
        self._task_count = task_count
        self._release_path = release_path

    def _create_tasks(self) -> List[Any]:
        return [
            CountingTask(
                index=index,
                report=self._task_reporter(index),
                release_path=self._release_path,
            )
            for index in range(self._task_count)
        ]

    def _get_task_function(self) -> Callable[[CountingTask], int]:
        return count_task

    def _process_results(self, results: List[int]) -> Tuple[int, ...]:
        return tuple(results)


class ProgressRecorder:
    """Keeps every reading a run offers, and waits for the one a test is after.

    A run reports from two threads — the one waiting on results and the one reading the channel —
    so the readings are gathered under a condition every arrival wakes. A test names the reading it
    wants and waits for it, which is how an assertion about work in flight is made while that work
    is provably still in flight.
    """

    def __init__(self) -> None:
        self.readings: List[Tuple[TaskStatus, TaskProgress]] = []
        self._condition = threading.Condition()

    def __call__(self, status: TaskStatus, progress: TaskProgress) -> None:
        with self._condition:
            self.readings.append((status, progress))
            self._condition.notify_all()

    def wait_for(self, matches: Callable[[TaskProgress], bool], timeout: float) -> bool:
        """Waits for a reading that matches, and answers whether the run offered one.

        Args:
            matches: What the test is waiting to see the run stand at.
            timeout: How long to wait for it.

        Returns:
            bool: Whether such a reading arrived within the time given.
        """
        with self._condition:
            return self._condition.wait_for(
                lambda: any(matches(progress) for _, progress in self.readings),
                timeout=timeout,
            )

    @property
    def fractions(self) -> List[float]:
        """How full the run stood at each reading taken while it ran, in the order they arrived.

        A run that has ended lets go of its counts, so the readings its teardown offers describe a
        processor standing ready rather than the run that just finished.
        """
        with self._condition:
            return [progress.fraction for status, progress in self.readings if status in LIVE_STATUSES]

    @property
    def steps(self) -> List[TaskStep]:
        """Every step a task filed, as the readings carried them."""
        with self._condition:
            return [step for _, progress in self.readings for step in progress.steps]

    def last_of(self, status: TaskStatus) -> Optional[TaskProgress]:
        """The final reading the run offered while it stood at ``status``."""
        with self._condition:
            matching = [progress for reading, progress in self.readings if reading == status]

        return matching[-1] if matching else None


def stands_partway(progress: TaskProgress) -> bool:
    """A run standing between its ends with no task yet finished, so the work is inside one."""
    return progress.completed == NOTHING_COMPLETED and 0.0 < progress.fraction < WHOLE_TASK


def several_tasks_reporting(progress: TaskProgress) -> bool:
    """More than one task standing on a line of its own at the same moment."""
    return len(progress.steps) > ONE_STEP
