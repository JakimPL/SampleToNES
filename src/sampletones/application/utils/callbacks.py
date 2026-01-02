import threading
import time
from collections import deque
from functools import wraps
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    List,
    NamedTuple,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from sampletones.typehints import Callback
from sampletones.utils.logger import logger

F = TypeVar("F", bound=Callback)

TASKS_PER_FRAME = 2
TIME_PER_FRAME = 0.005


class CallbackQueueStop(Exception):
    pass


class CallbackTask(NamedTuple):
    callback: Callback
    frame: int
    args: Tuple[Any, ...]
    kwargs: Dict[str, Any]


class CallbackQueue:
    _callbacks: Deque[CallbackTask] = deque()
    _lock: threading.Lock = threading.Lock()
    _processing_lock: threading.Lock = threading.Lock()
    _min_tasks_per_frame: int = TASKS_PER_FRAME
    _time_per_frame: float = TIME_PER_FRAME
    _frame_counter: int = 0

    @classmethod
    def add(
        cls,
        callback: Callback,
        *args: Any,
        priority: bool = False,
        delay: int = 0,
        **kwargs: Any,
    ) -> None:
        with cls._lock:
            frame = cls._frame_counter + delay
            task = CallbackTask(callback, frame, args, kwargs)
            if priority:
                cls._callbacks.appendleft(task)
            else:
                cls._callbacks.append(task)

    @classmethod
    def process(cls) -> None:
        if not cls._processing_lock.acquire(blocking=False):
            return
        try:
            cls._process()
        finally:
            cls._processing_lock.release()

    @classmethod
    def _process(cls) -> None:
        with cls._lock:
            cls._frame_counter += 1

        if not cls._callbacks:
            return

        tasks = 0
        stopped = False
        deadline = time.perf_counter() + cls._time_per_frame
        pending_tasks: List[CallbackTask] = []

        while not stopped:
            with cls._lock:
                if not cls._callbacks:
                    break

                task = cls._callbacks.popleft()

            callback, frame, args, kwargs = task
            if frame > cls._frame_counter:
                pending_tasks.append(task)
                continue

            tasks += 1
            stopped = cls.run(callback, *args, **kwargs)
            if time.perf_counter() >= deadline and tasks >= cls._min_tasks_per_frame:
                break

        with cls._lock:
            if stopped:
                cls.stop()
            else:
                for task in reversed(pending_tasks):
                    cls._callbacks.appendleft(task)

    @classmethod
    def stop(cls) -> None:
        with cls._lock:
            cls._callbacks.clear()

    @classmethod
    def run(cls, callback: Callback, *args: Any, **kwargs: Any) -> bool:
        try:
            callback(*args, **kwargs)
            return False
        except CallbackQueueStop as exception:
            logger.error(f"Callback queue processing stopped due to the error: {exception}.")
            return True
        except Exception as exception:
            logger.error_with_traceback(
                exception, f"Error executing callback {getattr(callback, '__name__', str(callback))}"
            )
            return False


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
