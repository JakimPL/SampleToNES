import atexit
import multiprocessing
import threading
from concurrent.futures._base import CancelledError
from typing import Any, Callable, Generic, List, Optional, TypeVar, Union

from pebble import ProcessMapFuture, ProcessPool

from constants.general import MAX_WORKERS
from utils.logger import logger
from utils.parallelization.task import TaskProgress, TaskStatus

T = TypeVar("T")

TIMEOUT = 1
CANCEL_TIMEOUT = 5
STOP_TIMEOUT = 2


class TaskProcessor(Generic[T]):
    def __init__(self, max_workers: Optional[int] = None) -> None:
        self.max_workers: int = max_workers or MAX_WORKERS
        self.pool: Optional[ProcessPool] = None
        self.future: Optional[ProcessMapFuture] = None
        self.monitor_thread: Optional[threading.Thread] = None

        self.status: TaskStatus = TaskStatus.PENDING
        self.running = False
        self.cancelling = False
        self.total_tasks = 0
        self.completed_tasks = 0
        self.current_item: Optional[str] = None

        self._on_progress: Optional[Callable[[TaskStatus, TaskProgress], None]] = None
        self._on_complete: Optional[Callable[[T], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        self._on_cancelled: Optional[Callable[[], None]] = None

        atexit.register(self.cleanup)

    def start(self, *args, **kwargs) -> None:
        raise NotImplementedError

    def _create_tasks(self) -> List[Any]:
        raise NotImplementedError

    def _get_task_function(self) -> Callable:
        raise NotImplementedError

    def _process_results(self, results: List[Any]) -> T:
        raise NotImplementedError

    def _reset_status(self) -> None:
        self.status = TaskStatus.PENDING
        self.running = False
        self.cancelling = False
        self.total_tasks = 0
        self.completed_tasks = 0
        self.current_item = None

    def _run_tasks(self) -> None:
        self._reset_status()
        tasks = self._create_tasks()
        self.total_tasks = len(tasks)
        self.completed_tasks = 0
        self._notify_progress()

        workers = self.max_workers
        context = multiprocessing.get_context("spawn")
        self.pool = ProcessPool(max_workers=workers, context=context)
        task_function = self._get_task_function()
        self.future = self.pool.map(task_function, tasks, timeout=None)

        logger.info("Starting the conversion process")
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
                self.completed_tasks += 1
                self._notify_progress()
        except StopIteration:
            pass
        except CancelledError:
            self._finalize_cancellation()
            return
        except Exception as exception:
            logger.error_with_traceback(f"Task failed: {exception}", exception)
            self._stop_with_error(str(exception))
            return
        finally:
            self.running = False

        self._finalize_completion(results)
        self._cleanup_pool()

    def _notify_progress(self) -> None:
        if self._on_progress is None:
            return

        progress = TaskProgress(
            total=self.total_tasks,
            completed=self.completed_tasks,
            current_item=self.current_item,
        )
        self._on_progress(self.status, progress)
        print(self.status, progress)

    def _finalize_cancellation(self) -> None:
        if not self.cancelling:
            return

        logger.info("Task processing was cancelled.")
        self.cancelling = False
        self.running = False
        self.status = TaskStatus.CANCELLED
        self._notify_progress()

        if self._on_cancelled:
            self._on_cancelled()

    def _finalize_completion(self, results: List[Any]) -> None:
        self.running = False
        self.status = TaskStatus.COMPLETED
        self._notify_progress()

        processed_result = self._process_results(results)
        if self._on_complete:
            self._on_complete(processed_result)

    def _stop_with_error(self, error_message: str) -> None:
        self.running = False
        self.status = TaskStatus.FAILED
        self._notify_progress()

        if self._on_error:
            self._on_error(str(error_message))

        self._stop_pool()

    def cancel(self) -> None:
        self.cancelling = True
        self.status = TaskStatus.CANCELLING
        self._notify_progress()

        if self.future:
            self.future.cancel()

        cancel_thread = threading.Thread(target=self._wait_for_cancellation, daemon=True)
        cancel_thread.start()

    def _is_thread_alive(self) -> bool:
        return self.monitor_thread is not None and self.monitor_thread.is_alive()

    def _wait_for_cancellation(self) -> None:
        if self._is_thread_alive():
            assert self.monitor_thread is not None, "Monitor thread expected to be alive"
            self.monitor_thread.join(timeout=CANCEL_TIMEOUT)

        self._finalize_cancellation()
        self._stop_pool(timeout=CANCEL_TIMEOUT)

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

    def set_callbacks(
        self,
        on_progress: Optional[Callable[[TaskStatus, TaskProgress], None]] = None,
        on_complete: Optional[Callable[[T], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_cancelled: Optional[Callable[[], None]] = None,
    ) -> None:
        if on_progress is not None:
            self._on_progress = on_progress
        if on_complete is not None:
            self._on_complete = on_complete
        if on_error is not None:
            self._on_error = on_error
        if on_cancelled is not None:
            self._on_cancelled = on_cancelled

    def cleanup(self) -> None:
        self.status = TaskStatus.CANCELLING
        self.running = False
        self.cancelling = True

        if self.future:
            self.future.cancel()

        self.status = TaskStatus.NONE

    def _cleanup_pool(self, timeout: Union[int, float] = STOP_TIMEOUT) -> None:
        self._notify_progress()
        if self.pool is not None:
            logger.info("Cleaning the task manager pool...")
            self.pool.close()
            self.pool.join(timeout=timeout)

    def _stop_pool(self, timeout: Union[int, float] = STOP_TIMEOUT) -> None:
        self._notify_progress()
        if self.pool is not None:
            logger.info("Stopping the task manager pool...")
            self.pool.stop()
            self.pool.join(timeout=timeout)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False

    def __del__(self):
        self.cleanup()
