from __future__ import annotations

import heapq
import threading
import time
from functools import wraps
from typing import Any, Callable, List, Optional, TypeVar, Union, cast

from sampletones.exceptions import CallbackQueueStop
from sampletones.typehints import Callback
from sampletones.utils.logger import logger

from .priority import CallbackPriority
from .task import CallbackTask

F = TypeVar("F", bound=Callback)

TASKS_PER_FRAME = 2
TIME_PER_FRAME = 1.0 / 120.0


class CallbackQueue:
    _callbacks: List[CallbackTask] = []
    _lock: threading.Lock = threading.Lock()
    _processing_lock: threading.Lock = threading.Lock()
    _min_tasks_per_frame: int = TASKS_PER_FRAME
    _time_per_frame: float = TIME_PER_FRAME
    _frame_counter: int = 0
    _insertion_counter: int = 0

    @classmethod
    def add(
        cls,
        callback: Callback,
        *args: Any,
        priority: int = 0,
        delay: int = 0,
        **kwargs: Any,
    ) -> None:
        with cls._lock:
            frame = cls._frame_counter + delay
            insertion_order = cls._insertion_counter
            cls._insertion_counter += 1
            task_priority = CallbackPriority(priority, frame, insertion_order)
            task = CallbackTask(task_priority, callback, args, kwargs)
            heapq.heappush(cls._callbacks, task)

    @classmethod
    def process(cls) -> None:
        with cls._processing_lock:
            cls._process()

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

                task = heapq.heappop(cls._callbacks)

            priority, callback, args, kwargs = task
            if priority.frame > cls._frame_counter:
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
                for task in pending_tasks:
                    heapq.heappush(cls._callbacks, task)

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
    priority: int,
    delay: int = 0,
) -> Union[F, Callable[[F], F]]:
    def decorator(function: F) -> F:

        @wraps(function)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> None:
            CallbackQueue.add(
                function,
                self,
                *args,
                priority=priority,
                delay=delay,
                **kwargs,
            )

        return cast(F, wrapper)

    return decorator if method is None else decorator(method)
