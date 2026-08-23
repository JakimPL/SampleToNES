import multiprocessing
import threading
from abc import ABC, abstractmethod
from concurrent.futures._base import CancelledError
from typing import Any, Callable, Final, Generic, List, Optional, TypeVar, Union

from pebble import ProcessMapFuture, ProcessPool

from sampletones_core.constants.algorithm import MAX_WORKERS
from sampletones_core.parallelization.channel.process import ProcessProgressChannel
from sampletones_core.parallelization.channel.protocol import ProgressChannel, StepReporter
from sampletones_core.parallelization.channel.pump import ProgressPump
from sampletones_core.parallelization.steps import TaskSteps
from sampletones_core.parallelization.task import (
    TaskProgress,
    TaskStatus,
)
from sampletones_shared.exceptions import OperationCancelled
from sampletones_shared.logger import LoggerProtocol
from sampletones_shared.logger import logger as default_logger
from sampletones_shared.types.callback import Callback, VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin

T = TypeVar("T")

CANCEL_TIMEOUT: Final[float] = 5.0
STOP_TIMEOUT: Final[float] = 2.0


class TaskProcessor(ABC, CallbackMixin, Generic[T]):
    def __init__(
        self,
        max_workers: Optional[int] = None,
        logger: LoggerProtocol = default_logger,
    ) -> None:
        self.max_workers: int = max_workers or MAX_WORKERS
        self.pool: Optional[ProcessPool] = None
        self.future: Optional[ProcessMapFuture] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.logger = logger

        self.status: TaskStatus = TaskStatus.PENDING
        self.running = False
        self.cancelling = False
        self.total_tasks = 0
        self.completed_tasks = 0
        self.current_item: Optional[str] = None

        self._notify_progress_lock = threading.Lock()
        self._pool_lock: threading.Lock = threading.Lock()
        self._exception: Optional[Exception] = None

        self._steps: TaskSteps = TaskSteps()
        self._channel_lock: threading.Lock = threading.Lock()
        self._channel: Optional[ProgressChannel] = None
        self._pump: Optional[ProgressPump] = None

        self.on_start: Optional[VoidCallback] = None
        self.on_progress: Optional[Callable[[TaskStatus, TaskProgress], None]] = None
        self.on_completed: Optional[Callable[[T], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_cancelled: Optional[VoidCallback] = None

    def start(self) -> None:
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

    def cleanup(self) -> None:
        self.status = TaskStatus.CLEANING_UP
        self.running = False
        self.cancelling = True

        self._withdraw()
        self._notify_progress()
        self._cleanup()

    def cancel(self) -> None:
        self.status = TaskStatus.CANCELLING
        self.cancelling = True

        self._withdraw()
        self._notify_progress()
        self._cleanup()

    def shutdown(self) -> None:
        """Stops the pool and reaps its workers on the calling thread before returning.

        Cancelling from the interface tears the pool down on a background thread to keep
        the interface responsive. At application exit the process is about to release the
        shared resources the pool's spawned workers rely on, so the teardown runs inline
        here and returns only once the pool has stopped."""
        self.status = TaskStatus.CLEANING_UP
        self.running = False
        self.cancelling = True

        self._withdraw()
        self._notify_progress()
        if self.future is not None:
            self.future.cancel()

        self._stop_pool()
        self._join_thread()
        self._release_channel()
        self._reset_status()

    def is_running(self) -> bool:
        return self.running

    def is_completed(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    def is_cancelled(self) -> bool:
        return self.status == TaskStatus.CANCELLED

    def is_cancelling(self) -> bool:
        return self.status == TaskStatus.CANCELLING

    def is_failed(self) -> bool:
        return self.status == TaskStatus.FAILED

    def get_status(self) -> TaskStatus:
        return self.status

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
        """Ends the reading and the channel, which the run does once its tasks are all heard from.

        Every way a run can end reaches here, including one that built its tasks and never started,
        since the channel is a process of its own to be reaped whatever became of the run.
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
        self.cancelling = False
        self.total_tasks = 0
        self.completed_tasks = 0
        self.current_item = None

    def _run_tasks(self) -> None:
        """Runs the tasks and holds the progress channel for exactly as long as they do."""
        try:
            self._process_tasks()
        finally:
            self._release_channel()

    def _process_tasks(self) -> None:
        self._reset_status()

        try:
            tasks = self._create_tasks()
        except Exception as exception:
            self._stop_with_error(exception)
            return

        self.total_tasks = len(tasks)
        self.completed_tasks = 0

        self.logger.info("Starting processing tasks...")
        self._notify_progress()

        workers = self.max_workers
        context = multiprocessing.get_context("spawn")
        self.pool = ProcessPool(max_workers=workers, context=context)
        task_function = self._get_task_function()
        self.future = self.pool.map(task_function, tasks, timeout=None)
        self._start_pump()
        self.call(self.on_start)

        results = []
        try:
            self.running = True
            self.status = TaskStatus.RUNNING
            self._notify_progress()
            iterator = self.future.result()

            while True:
                if self.cancelling:
                    raise CancelledError()

                result = next(iterator)
                results.append(result)
                self._steps.complete(self.completed_tasks)
                self.completed_tasks += 1
                self._notify_progress()
        except StopIteration:
            pass
        except KeyboardInterrupt as exception:
            raise CancelledError() from exception
        except OperationCancelled:
            self._finalize_cancellation()
            return
        except CancelledError:
            self._finalize_cancellation()
            return
        except Exception as exception:
            self._stop_with_error(exception)
            return
        finally:
            self.running = False

        self._complete_process(results)

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
        if not self.cancelling:
            return

        self.logger.info("Task processing was cancelled.")
        self.status = TaskStatus.CANCELLED
        self.cancelling = False
        self.running = False
        self._notify_progress()
        self.call(self.on_cancelled)

    def _finalize_completion(self, results: List[T]) -> None:
        self.logger.info("Conversion completed successfully")

        self.status = TaskStatus.COMPLETED
        self.running = False
        self._notify_progress()

        processed_result = self._process_results(results)
        self.call(self.on_completed, processed_result)

    def _stop_with_error(self, exception: Exception) -> None:
        self.logger.error_with_traceback(exception, f"Task failed: {exception}")

        self._exception = exception
        self.status = TaskStatus.FAILED
        self.running = False
        self._notify_progress()
        self.call(self.on_error, exception)

    def _cleanup(self) -> None:
        if self.future:
            self.future.cancel()

        cleanup_thread = threading.Thread(
            target=self._wait_for_cleanup,
            daemon=True,
            name="TaskProcessorCleanup",
        )
        cleanup_thread.start()

    def _is_thread_alive(self) -> bool:
        return self.monitor_thread is not None and self.monitor_thread.is_alive()

    def _join_thread(self) -> None:
        if self._is_thread_alive():
            assert self.monitor_thread is not None, "Monitor thread expected to be alive"
            self.monitor_thread.join(timeout=CANCEL_TIMEOUT)

    def _wait_for_cleanup(self) -> None:
        self._stop_pool()
        self._join_thread()
        self._release_channel()
        self._reset_status()

    def _complete_process(self, results: List[T]) -> None:
        self._finalize_completion(results)
        self._cleanup_pool()
        self._reset_status()

    def _join_pool(self, timeout: Optional[Union[int, float]] = None) -> None:
        try:
            if self.pool is not None:
                if timeout is not None:
                    self.pool.join(timeout=timeout)
                else:
                    self.pool.join()
        except OSError as exception:
            self.logger.error_with_traceback(exception, f"Error while joining the pool: {exception}")

    def _cleanup_pool(self) -> None:
        self._notify_progress()
        if self.pool is None:
            return

        with self._pool_lock:
            self.logger.info("Cleaning the task manager pool...")
            try:
                self.pool.close()  # type: ignore[no-untyped-call]
            except RuntimeError as exception:
                self.logger.error_with_traceback(exception, f"Error while closing the pool: {exception}")
            finally:
                self._join_pool()

    def _stop_pool(self, timeout: float = STOP_TIMEOUT) -> None:
        self._notify_progress()
        if self.pool is None:
            return

        with self._pool_lock:
            self.logger.info("Stopping the task manager pool...")
            try:
                self.pool.stop()  # type: ignore[no-untyped-call]
            except RuntimeError as exception:
                self.logger.error_with_traceback(exception, f"Error while stopping the pool: {exception}")
            finally:
                self._join_pool(timeout=timeout)
