import threading
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, Union, cast

from sampletones.typehints import Callback, VoidCallback

F = TypeVar("F", bound=Callback)


class SingleThreadExecutor:
    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._pending_task: Optional[VoidCallback] = None

    def execute(self, target: VoidCallback, wait: bool = True) -> bool:
        with self._lock:
            self._pending_task = target
            current_thread = self._thread

        if current_thread is not None and current_thread.is_alive():
            if wait:
                self._pending_task = target

            return False

        with self._lock:
            self._thread = threading.Thread(target=target, daemon=True)
            self._thread.start()
            return True


def concurrent(
    method: Optional[F] = None,
    *,
    wait: bool = True,
    method_bound: bool = False,
) -> Union[F, Callable[[F], F]]:
    def decorator(func: F) -> F:
        method_class = func.__qualname__.split(".")[0]
        method_name = func.__name__
        if method_bound:
            executor_attribute = f"_concurrent_executor_{method_class}_{method_name}"
        else:
            executor_attribute = f"_concurrent_executor_{method_class}"

        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> None:
            if not hasattr(self, executor_attribute):
                setattr(self, executor_attribute, SingleThreadExecutor())

            executor: SingleThreadExecutor = getattr(self, executor_attribute)

            def task() -> None:
                func(self, *args, **kwargs)

            executor.execute(task, wait=wait)

        return cast(F, wrapper)

    return decorator if method is None else decorator(method)
