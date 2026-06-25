from __future__ import annotations

import threading
import weakref
from functools import wraps
from typing import Any, Callable, Optional, cast

from sampletones_shared.logger import logger
from sampletones_shared.types.callback import CallbackT, VoidCallback


class SingleThreadExecutor:
    _instances: weakref.WeakSet[SingleThreadExecutor] = weakref.WeakSet()
    _instances_lock = threading.Lock()

    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        with SingleThreadExecutor._instances_lock:
            SingleThreadExecutor._instances.add(self)

    def execute(self, target: VoidCallback, wait: bool = True) -> bool:
        with self._lock:
            current_thread = self._thread

        if current_thread is not None and current_thread.is_alive():
            if wait:
                current_thread.join()
            else:
                return False

        with self._lock:
            self._thread = threading.Thread(
                target=target,
                daemon=True,
                name="ExecutorWorker",
            )
            self._thread.start()
            return True

    def join(self, timeout: Optional[float] = None) -> None:
        with self._lock:
            thread = self._thread

        if thread is not None and thread.is_alive():
            thread.join(timeout)

    @classmethod
    def join_all(cls, timeout: Optional[float] = None) -> None:
        """Wait for every executor's in-flight task to finish.

        Background tasks touch non-thread-safe resources (e.g. dearpygui), so
        they must be awaited before the GUI context is torn down.
        """
        with cls._instances_lock:
            instances = list(cls._instances)

        for instance in instances:
            instance.join(timeout)


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
                try:
                    function(self, *args, **kwargs)
                except Exception as exception:
                    logger.error_with_traceback(
                        exception,
                        f"Error in background task {function.__qualname__}",
                    )

            executor.execute(task, wait=wait)

        return cast(CallbackT, wrapper)

    return decorator
