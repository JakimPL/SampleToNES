import threading
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])


class SingleThreadExecutor:
    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def execute(self, target: Callable[[], None]) -> bool:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return False

            self._thread = threading.Thread(target=target, daemon=True)
            self._thread.start()
            return True

    def is_running(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()


def concurrent(method: F) -> F:
    executor_attr = f"_concurrent_executor_{method.__name__}"

    @wraps(method)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> None:
        if not hasattr(self, executor_attr):
            setattr(self, executor_attr, SingleThreadExecutor())

        executor: SingleThreadExecutor = getattr(self, executor_attr)

        def task() -> None:
            method(self, *args, **kwargs)

        executor.execute(task)

    return cast(F, wrapper)
