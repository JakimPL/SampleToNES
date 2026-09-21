import multiprocessing
import threading
from abc import ABC, abstractmethod
from concurrent.futures._base import CancelledError
from typing import Any, Callable, Final, Generic, List, Optional, TypeVar

from pebble import ProcessMapFuture, ProcessPool

from sampletones_core.constants.algorithm import MAX_WORKERS
from sampletones_core.parallelization.channel.process import ProcessProgressChannel
from sampletones_core.parallelization.channel.protocol import ProgressChannel, StepReporter
from sampletones_core.parallelization.channel.pump import ProgressPump
from sampletones_core.parallelization.outcome import RunCanceled, RunCompleted, RunFailed, RunOutcome
from sampletones_core.parallelization.steps import TaskSteps
from sampletones_core.parallelization.task import (
    TaskProgress,
    TaskStatus,
)
from sampletones_shared.exceptions import OperationCanceled
from sampletones_shared.logger import LoggerProtocol
from sampletones_shared.logger import logger as default_logger
from sampletones_shared.types.callback import Callback, VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin

T = TypeVar("T")

SPAWN_CONTEXT: Final[str] = "spawn"


class TaskProcessor(ABC, CallbackMixin, Generic[T]):
    """Runs a list of tasks on a process pool that its monitor thread alone owns.

    The monitor thread builds the tasks, creates the pool, gathers the answers and, however the run
    ends, ends the pool and the progress channel before it announces the outcome. Whoever reacts to
    ``on_completed``, ``on_canceled`` or ``on_error`` therefore meets a run with no worker left.
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        logger: LoggerProtocol = default_logger,
    ) -> None:
        self.max_workers: int = max_workers or MAX_WORKERS
        self.future: Optional[ProcessMapFuture] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.logger = logger

        self.status: TaskStatus = TaskStatus.PENDING
        self.running = False
        self.canceling = False
        self.total_tasks = 0
        self.completed_tasks = 0
        self.current_item: Optional[str] = None

        self._notify_progress_lock = threading.Lock()
        self._exception: Optional[Exception] = None

        self._steps: TaskSteps = TaskSteps()
        self._channel_lock: threading.Lock = threading.Lock()
        self._channel: Optional[ProgressChannel] = None
        self._pump: Optional[ProgressPump] = None

        self.on_start: Optional[VoidCallback] = None
        self.on_progress: Optional[Callable[[TaskStatus, TaskProgress], None]] = None
        self.on_completed: Optional[Callable[[T], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_canceled: Optional[VoidCallback] = None

    def start(self) -> None:
        self._reset_status()
        self.monitor_thread = threading.Thread(
            target=self._run_tasks,
            daemon=True,
            name="TaskProcessorMonitor",
        )
        self.monitor_thread.start()

    def wait(self, timeout: Optional[float] = None) -> None:
        if self.monitor_thread is None:
            return

        self.monitor_thread.join(timeout=timeout)
        if self._exception is not None:
            raise self._exception

    def cancel(self) -> None:
        """Withdraws the run; the monitor thread answers by stopping the pool and announcing it."""
        self.status = TaskStatus.CANCELING
        self.canceling = True

        self._withdraw()
        self._notify_progress()
        future = self.future
        if future is not None:
            future.cancel()

    def shutdown(self) -> None:
        """Ends the run and returns once its pool and its channel have ended.

        A run still in progress is canceled and its monitor thread joined; a run whose monitor has
        already announced its outcome returns at once. A run whose tasks were built and never
        started holds a channel all the same, which ends here.
        """
        monitor = self.monitor_thread
        if monitor is not None and monitor.is_alive():
            self.cancel()
            monitor.join()

        self._release_channel()

    def is_running(self) -> bool:
        return self.running

    @abstractmethod
    def _create_tasks(self) -> List[Any]: ...

    @abstractmethod
    def _get_task_function(self) -> Callback: ...

    @abstractmethod
    def _process_results(self, results: List[T]) -> Any: ...

    def _task_reporter(self, index: int) -> StepReporter:
        """The line the task at ``index`` reports its own progress on.

        A subclass whose tasks find their way through work the run cannot see asks for one per task
        as it builds them. The channel those lines run through is opened on the first ask, so a run
        whose tasks report nothing costs nothing to listen to.
        """
        with self._channel_lock:
            if self._channel is None:
                self._channel = ProcessProgressChannel()

            return self._channel.reporter(index)

    def _withdraw(self) -> None:
        """Tells the running tasks the run has let go of the answer they were building."""
        with self._channel_lock:
            if self._channel is not None:
                self._channel.withdraw()

    def _start_pump(self) -> None:
        with self._channel_lock:
            if self._channel is None:
                return

            self._pump = ProgressPump(
                self._channel,
                record=self._steps.record,
                announce=self._notify_progress,
                logger=self.logger,
            )

        self._pump.start()

    def _release_channel(self) -> None:
        """Ends the reading and the channel, which the run does once its workers have ended.

        The channel's manager is a process of its own that the workers hold proxies to, so it ends
        after the pool, and every ending reaches here, including a run that built its tasks and
        never started.
        """
        with self._channel_lock:
            if self._pump is not None:
                self._pump.stop()
                self._pump = None

            if self._channel is not None:
                self._channel.close()
                self._channel = None

        self._steps.clear()

    def _reset_status(self) -> None:
        self.status = TaskStatus.PENDING
        self.running = False
        self.canceling = False
        self.total_tasks = 0
        self.completed_tasks = 0
        self.current_item = None

    def _run_tasks(self) -> None:
        """Gathers the run, ends the channel once the pool has ended, then announces the outcome."""
        try:
            outcome = self._gather()
        finally:
            self._release_channel()

        self._announce(outcome)

    def _gather(self) -> RunOutcome[T]:
        """Builds the tasks and runs them on a pool that has ended by the time this returns."""
        try:
            tasks = self._create_tasks()
        except Exception as exception:
            return RunFailed(exception)

        if self.canceling:
            return RunCanceled()

        self.total_tasks = len(tasks)
        self.completed_tasks = 0

        self.logger.info("Starting processing tasks...")
        self._notify_progress()

        pool = ProcessPool(
            max_workers=self.max_workers,
            context=multiprocessing.get_context(SPAWN_CONTEXT),
        )
        outcome: Optional[RunOutcome[T]] = None
        try:
            outcome = self._drain(pool, tasks)
            return outcome
        finally:
            self._end_pool(pool, outcome)

    def _drain(
        self,
        pool: ProcessPool,
        tasks: List[Any],
    ) -> RunOutcome[T]:
        """Hands the tasks to ``pool`` and collects their answers until they are all in or withdrawn."""
        self.future = pool.map(self._get_task_function(), tasks, timeout=None)
        self._start_pump()
        self.call(self.on_start)

        results: List[T] = []
        self.running = True
        self.status = TaskStatus.RUNNING
        self._notify_progress()
        try:
            iterator = self.future.result()
            while not self.canceling:
                results.append(next(iterator))
                self._steps.complete(self.completed_tasks)
                self.completed_tasks += 1
                self._notify_progress()
        except StopIteration:
            return RunCompleted(results)
        except (CancelledError, OperationCanceled):
            return RunCanceled()
        except Exception as exception:
            return RunFailed(exception)
        finally:
            self.running = False

        return RunCanceled()

    def _end_pool(
        self,
        pool: ProcessPool,
        outcome: Optional[RunOutcome[T]],
    ) -> None:
        """Lets a pool whose every task answered wind down, stops any other, and reaps its workers."""
        if isinstance(outcome, RunCompleted):
            self.logger.info("Closing the task manager pool...")
            pool.close()  # type: ignore[no-untyped-call]
        else:
            self.logger.info("Stopping the task manager pool...")
            pool.stop()  # type: ignore[no-untyped-call]

        pool.join()

    def _announce(self, outcome: RunOutcome[T]) -> None:
        match outcome:
            case RunCompleted(results=results):
                self._finalize_completion(results)
            case RunCanceled():
                self._finalize_cancellation()
            case RunFailed(exception=exception):
                self._stop_with_error(exception)

    def _notify_progress(self) -> None:
        with self._notify_progress_lock:
            if self.on_progress is None:
                return

            progress = TaskProgress(
                total=self.total_tasks,
                completed=self.completed_tasks,
                current_item=self.current_item,
                steps=self._steps.snapshot(),
            )

            self.call(self.on_progress, self.status, progress)
            self.logger.debug(f"Status: {self.status}; progress: {progress}")

    def _finalize_cancellation(self) -> None:
        self.logger.info("Task processing was canceled.")
        self.status = TaskStatus.CANCELED
        self.canceling = False
        self._notify_progress()
        self.call(self.on_canceled)

    def _finalize_completion(self, results: List[T]) -> None:
        self.logger.info("Conversion completed successfully")

        self.status = TaskStatus.COMPLETED
        self._notify_progress()

        processed_result = self._process_results(results)
        self.call(self.on_completed, processed_result)

    def _stop_with_error(self, exception: Exception) -> None:
        self.logger.error_with_traceback(exception, f"Task failed: {exception}")

        self._exception = exception
        self.status = TaskStatus.FAILED
        self._notify_progress()
        self.call(self.on_error, exception)
