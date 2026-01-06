from __future__ import annotations

import heapq
import threading
from functools import wraps
from typing import Any, Callable, List, Optional, TypeVar, Union, cast

from sampletones.exceptions import CallbackQueueStop
from sampletones.typehints import Callback
from sampletones.utils.logger import logger

from .priority import CallbackPriority
from .task import CallbackTask

F = TypeVar("F", bound=Callback)


class CallbackQueue:
    _callbacks: List[CallbackTask] = []
    _lock: threading.Lock = threading.Lock()
    _condition: threading.Condition = threading.Condition(_lock)
    _processing_lock: threading.Lock = threading.Lock()
    _frame_counter: int = 0
    _insertion_counter: int = 0
    _frame_updated: bool = False

    @classmethod
    def add(
        cls,
        callback: Callback,
        *args: Any,
        priority: int = 0,
        delay: int = 0,
        **kwargs: Any,
    ) -> None:
        with cls._condition:
            frame = cls._frame_counter + delay
            insertion_order = cls._insertion_counter
            cls._insertion_counter += 1
            task_priority = CallbackPriority(priority, frame, insertion_order)
            task = CallbackTask(task_priority, callback, args, kwargs)
            heapq.heappush(cls._callbacks, task)
            cls._condition.notify()

    @classmethod
    def notify_frame(cls) -> None:
        with cls._condition:
            cls._frame_counter += 1
            cls._frame_updated = True
            cls._condition.notify()

    @classmethod
    def process(cls) -> None:
        with cls._processing_lock:
            cls._process()

    @classmethod
    def _process(cls) -> None:
        while True:
            task = None
            frame_before = None

            with cls._condition:
                frame_before = cls._frame_counter

                if cls._callbacks and cls._callbacks[0].priority.frame <= cls._frame_counter:
                    task = heapq.heappop(cls._callbacks)
                else:
                    cls._condition.wait(timeout=0.01)
                    continue

            if task:
                _, callback, args, kwargs = task
                stopped = cls.run(callback, *args, **kwargs)

                if stopped:
                    cls.stop()
                    return

                with cls._condition:
                    if cls._frame_counter != frame_before:
                        return

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
