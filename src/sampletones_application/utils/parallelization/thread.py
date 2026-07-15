from __future__ import annotations

import threading
import time
from functools import wraps
from typing import Any, Callable, List, Optional, Set, cast

from sampletones_shared.logger import logger
from sampletones_shared.types.callback import CallbackT, VoidCallback


class BackgroundWorkCancelled(Exception):
    """Unwinds a background task promptly once shutdown has been requested.

    Long-running tasks poll :meth:`SingleThreadExecutor.is_shutting_down` at their
    cancellation points and raise this to abandon the remaining work, so teardown
    joins the worker in milliseconds instead of waiting out its natural duration.
    """


class SingleThreadExecutor:
    _live_threads: Set[threading.Thread] = set()
    _live_threads_lock = threading.Lock()
    _shutdown = threading.Event()

    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def execute(self, target: VoidCallback, wait: bool = True) -> bool:
        with self._lock:
            current_thread = self._thread

        if current_thread is not None and current_thread.is_alive():
            if wait:
                current_thread.join()
            else:
                return False

        def run_and_release() -> None:
            try:
                target()
            finally:
                with SingleThreadExecutor._live_threads_lock:
                    SingleThreadExecutor._live_threads.discard(threading.current_thread())

        with self._lock:
            thread = threading.Thread(
                target=run_and_release,
                daemon=True,
                name="ExecutorWorker",
            )
            self._thread = thread
            with SingleThreadExecutor._live_threads_lock:
                SingleThreadExecutor._live_threads.add(thread)

            thread.start()
            return True

    @classmethod
    def request_shutdown(cls) -> None:
        """Signal running background tasks to wind down at their next cancellation point.

        Set before :meth:`join_all` at teardown so an in-flight task raises
        :class:`BackgroundWorkCancelled` and finishes promptly, rather than the join
        blocking until the task completes on its own.
        """
        cls._shutdown.set()

    @classmethod
    def is_shutting_down(cls) -> bool:
        return cls._shutdown.is_set()

    @classmethod
    def reset_shutdown(cls) -> None:
        """Re-arm the executor for a fresh run, clearing a prior shutdown request."""
        cls._shutdown.clear()

    @classmethod
    def join_all(cls, timeout: Optional[float] = None) -> None:
        """Wait until every executor worker thread has finished.

        Background tasks touch non-thread-safe resources (e.g. dearpygui), so
        teardown must reach full quiescence before those resources are
        destroyed. Workers are tracked in a class-level registry of live
        threads, which keeps them joinable for as long as they run even when
        their owning executor has already been garbage collected. Joining
        proceeds in rounds until the registry drains, so workers spawned while
        a round is in progress are still awaited. With a timeout, joining
        stops at the deadline and the surviving workers are logged.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            with cls._live_threads_lock:
                live_threads = [thread for thread in cls._live_threads if thread.is_alive()]

            if not live_threads:
                return

            for thread in live_threads:
                remaining: Optional[float] = None
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0.0:
                        cls._report_surviving_workers(live_threads)
                        return
                thread.join(remaining)

    @classmethod
    def _report_surviving_workers(cls, threads: List[threading.Thread]) -> None:
        names = ", ".join(thread.name for thread in threads if thread.is_alive())
        if names:
            logger.warning(f"Background workers still running after the shutdown deadline: {names}")


def concurrent(
    wait: bool = True,
    method_bound: bool = False,
) -> Callable[[CallbackT], CallbackT]:
    def decorator(function: CallbackT) -> CallbackT:
        method_class = function.__qualname__.split(".")[0]
        method_name = function.__name__
        if method_bound:
            executor_attribute = f"_concurrent_executor_{method_class}_{method_name}"
        else:
            executor_attribute = f"_concurrent_executor_{method_class}"

        @wraps(function)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> None:
            if not hasattr(self, executor_attribute):
                setattr(self, executor_attribute, SingleThreadExecutor())

            executor: SingleThreadExecutor = getattr(self, executor_attribute)

            def task() -> None:
                if SingleThreadExecutor.is_shutting_down():
                    return
                try:
                    function(self, *args, **kwargs)
                except BackgroundWorkCancelled:
                    return
                except Exception as exception:  # pylint: disable=broad-exception-caught
                    logger.error_with_traceback(
                        exception,
                        f"Error in background task {function.__qualname__}",
                    )

            executor.execute(task, wait=wait)

        return cast(CallbackT, wrapper)

    return decorator
