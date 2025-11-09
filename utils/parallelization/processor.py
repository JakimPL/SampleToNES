import atexit
import threading
from typing import Any, Callable, Generic, List, Optional, TypeVar

from pebble import ProcessPool

from constants.general import MAX_WORKERS
from utils.logger import logger
from utils.parallelization.task import TaskProgress

T = TypeVar("T")


class TaskProcessor(Generic[T]):
    def __init__(self, max_workers: Optional[int] = None) -> None:
        self.max_workers: int = max_workers or MAX_WORKERS
        self.pool: Optional[ProcessPool] = None
        self.future: Optional[Any] = None
        self.monitor_thread: Optional[threading.Thread] = None

        self.running = False
        self.cancelling = False
        self.total_tasks = 0
        self.completed_tasks = 0
        self.current_item: Optional[str] = None

        self._on_progress: Optional[Callable[[TaskProgress], None]] = None
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

    def _run_tasks(self) -> None:
        tasks = self._create_tasks()
        self.total_tasks = len(tasks)
        self.completed_tasks = 0

        self._notify_progress()

        workers = self.max_workers
        self.pool = ProcessPool(max_workers=workers)
        task_function = self._get_task_function()
        self.future = self.pool.map(task_function, tasks, timeout=None)

        results = []
        try:
            iterator = self.future.result()
            while True:
                if self.cancelling:
                    break

                try:
                    result = next(iterator)
                    results.append(result)
                    self.completed_tasks += 1
                    self._notify_progress()
                except StopIteration:
                    break
                except Exception as exception:  # TODO: specify exception type
                    if self.cancelling:
                        self._finalize_cancellation()
                    else:
                        logger.error_with_traceback(f"Task failed: {exception}")
                        self.running = False
                        self.stop_with_error(str(exception))

                    return
        finally:
            self.pool.close()
            self.pool.join()

        self.running = False
        if self.cancelling:
            self._finalize_cancellation()
        else:
            result = self._process_results(results)
            if self._on_complete:
                self._on_complete(result)

    def _notify_progress(self) -> None:
        if self._on_progress:
            progress = TaskProgress(
                total=self.total_tasks,
                completed=self.completed_tasks,
                current_item=self.current_item,
            )
            self._on_progress(progress)

    def _finalize_cancellation(self) -> None:
        if self._on_cancelled:
            self._on_cancelled()
        self.running = False

    def stop_with_error(self, error_message: str) -> None:
        self.running = False
        if self._on_error:
            self._on_error(str(error_message))

    def cancel(self) -> None:
        if self.cancelling:
            return

        self.cancelling = True
        if self.future:
            self.future.cancel()

        cancel_thread = threading.Thread(target=self._wait_for_cancellation, daemon=True)
        cancel_thread.start()

    def _wait_for_cancellation(self) -> None:
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)

        if self.pool:
            self.pool.stop()
            self.pool.join()

        self.running = False

    def is_running(self) -> bool:
        return self.running

    def is_cancelling(self) -> bool:
        return self.cancelling

    def get_progress(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.completed_tasks / self.total_tasks

    def set_callbacks(
        self,
        on_progress: Optional[Callable[[TaskProgress], None]] = None,
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
        self.running = False
        self.cancelling = True

        if self.future:
            self.future.cancel()

        if self.pool:
            self.pool.stop()
            self.pool.join()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False

    def __del__(self):
        self.cleanup()
