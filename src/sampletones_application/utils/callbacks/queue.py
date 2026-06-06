from __future__ import annotations

import heapq
import threading
from functools import wraps
from typing import Any, Callable, List, Optional, Union, cast

from sampletones_application.utils.callbacks.priority import CallbackPriority
from sampletones_application.utils.callbacks.task import CallbackTask
from sampletones_shared.exceptions import CallbackQueueStop
from sampletones_shared.logger import logger
from sampletones_shared.meta import NonInstantiableMeta
from sampletones_shared.types.callback import Callback, CallbackT


class CallbackQueue(metaclass=NonInstantiableMeta):
    """Thread-safe priority queue that delivers background results to the main thread.

    The application runs long-running operations (file conversion, waveform
    regeneration, export) on background threads.  Those threads must never touch
    DPG or mutate UI state directly.  ``CallbackQueue`` is the sole mechanism
    for crossing the thread boundary: a background thread posts a callback with
    ``add()``, and the main-thread event loop drains the queue each frame.

    Responsibilities:
    - Accept callbacks posted from any thread (``add``), attaching a priority
      and an optional frame-delay.
    - Process due callbacks on the main thread each frame (``process``), in
      ascending priority order and then insertion order.
    - Run a background worker thread that continuously processes any ready
      callbacks (``start`` / ``stop``).
    - Isolate individual callback failures so that one bad callback cannot
      prevent subsequent ones from running.

    Governing principles:
    - Every service result must reach the logic layer through this queue, never
      by calling a handler directly from the background thread.
    - Priority values are integers where lower numbers run first.  Coordination
      priorities are defined in ``LayoutConfig.behavior.scheduling``.
    - The class is non-instantiable (``NonInstantiableMeta``); all state and
      methods are class-level.

    Dependencies: ``CallbackTask``, ``CallbackPriority``, ``threading``.
    """

    _callbacks: List[CallbackTask] = []
    _lock: threading.Lock = threading.Lock()
    _condition: threading.Condition = threading.Condition(_lock)
    _processing_lock: threading.Lock = threading.Lock()
    _frame_counter: int = 0
    _insertion_counter: int = 0
    _worker_thread: Optional[threading.Thread] = None
    _stop_event: threading.Event = threading.Event()
    _frame_updated: bool = False

    @classmethod
    def start(cls) -> None:
        if cls._worker_thread is not None and cls._worker_thread.is_alive():
            return

        cls._stop_event.clear()
        cls._worker_thread = threading.Thread(
            target=cls._worker,
            daemon=True,
            name="CallbackQueueWorker",
        )
        cls._worker_thread.start()
        logger.debug("Callback queue worker thread started")

    @classmethod
    def _worker(cls) -> None:
        while not cls._stop_event.is_set():
            cls.process()
            cls._stop_event.wait(timeout=0.01)

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
        cls._stop_event.set()
        with cls._condition:
            cls._callbacks.clear()
            cls._condition.notify()

        if cls._worker_thread and cls._worker_thread.is_alive():
            cls._worker_thread.join(timeout=0.1)
            logger.debug("Callback queue worker thread stopped")

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
                exception,
                f"Error executing callback {getattr(callback, '__name__', str(callback))}",
            )
            return False


def queued(
    method: Optional[CallbackT] = None,
    *,
    priority: int,
    delay: int = 0,
) -> Union[CallbackT, Callable[[CallbackT], CallbackT]]:
    def decorator(function: CallbackT) -> CallbackT:

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

        return cast(CallbackT, wrapper)

    return decorator if method is None else decorator(method)
