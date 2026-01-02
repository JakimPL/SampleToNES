import threading
import time
from collections import deque
from functools import wraps
from typing import Any, Callable, Deque, Dict, Optional, Tuple, TypeVar, Union, cast

from sampletones.typehints import Callback
from sampletones.utils.logger import logger

F = TypeVar("F", bound=Callback)

TASKS_PER_FRAME = 2
TIME_PER_FRAME = 0.002


class CallbackQueueStop(Exception):
    pass


class CallbackQueue:
    _callbacks: Deque[Tuple[Callback, Tuple[Any, ...], Dict[str, Any]]] = deque()
    _main_thread: threading.Thread = threading.main_thread()
    _lock: threading.Lock = threading.Lock()
    _tasks_per_frame: int = TASKS_PER_FRAME
    _time_per_frame: float = TIME_PER_FRAME

    @classmethod
    def add(
        cls,
        callback: Callback,
        *args: Any,
        priority: bool = False,
        **kwargs: Any,
    ) -> None:
        with cls._lock:
            if priority:
                cls._callbacks.appendleft((callback, args, kwargs))
            else:
                cls._callbacks.append((callback, args, kwargs))

    @classmethod
    def process(cls) -> None:
        assert threading.current_thread() == cls._main_thread, "Callbacks must be run on the main thread."
        if not cls._callbacks:
            return

        tasks = 0
        deadline = time.perf_counter() + cls._time_per_frame
        while (time.perf_counter() < deadline or tasks < cls._tasks_per_frame) and cls._callbacks:
            with cls._lock:
                callback, args, kwargs = cls._callbacks.popleft()
            try:
                callback(*args, **kwargs)
                tasks += 1
            except CallbackQueueStop as exception:
                logger.error(f"Callback queue processing stopped due to the error: {exception}.")
                break


def queued(
    method: Optional[F] = None,
    *,
    priority: bool = False,
) -> Union[F, Callable[[F], F]]:
    def decorator(function: F) -> F:

        @wraps(function)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> None:
            CallbackQueue.add(
                function,
                self,
                *args,
                priority=priority,
                **kwargs,
            )

        return cast(F, wrapper)

    return decorator if method is None else decorator(method)
