import threading
from collections import deque
from typing import Any, Deque, Dict, Tuple

from sampletones.typehints import Callback
from sampletones.utils.logger import logger

TASKS_PER_FRAME = 25


class CallbackQueueStop(Exception):
    pass


class CallbackQueue:
    _callbacks: Deque[Tuple[Callback, Tuple[Any, ...], Dict[str, Any]]] = deque()
    _main_thread: threading.Thread = threading.main_thread()
    _lock: threading.Lock = threading.Lock()
    _tasks_per_frame: int = TASKS_PER_FRAME

    @classmethod
    def add(cls, callback: Callback, *args: Any, **kwargs: Any) -> None:
        with cls._lock:
            cls._callbacks.appendleft((callback, args, kwargs))

    @classmethod
    def process(cls) -> None:
        assert threading.current_thread() == cls._main_thread, "Callbacks must be run on the main thread."
        for _ in range(min(cls._tasks_per_frame, len(cls._callbacks))):
            with cls._lock:
                callback, args, kwargs = cls._callbacks.pop()
            try:
                callback(*args, **kwargs)
            except CallbackQueueStop as exception:
                logger.error(f"Callback queue processing stopped due to the error: {exception}.")
                break


def queued(function: Callback) -> Callback:
    def wrapper(self, *args: Any, **kwargs: Any) -> None:
        CallbackQueue.add(function, self, *args, **kwargs)

    return wrapper
