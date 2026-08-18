from __future__ import annotations

import heapq
import threading
import time
from typing import Any, ClassVar, List

from sampletones_application.utils.callbacks.priority import CallbackPriority
from sampletones_application.utils.callbacks.task import CallbackTask
from sampletones_shared.exceptions import CallbackQueueStop
from sampletones_shared.logger import logger
from sampletones_shared.meta import NonInstantiableMeta
from sampletones_shared.types.callback import Callback


class CallbackQueue(metaclass=NonInstantiableMeta):
    """
    The sole channel delivering background-thread results to the main thread.

    Producers on any thread post callbacks with a priority through :meth:`add`.
    The main-thread render loop advances the frame counter once per rendered
    frame with :meth:`notify_frame` and drains the due callbacks with
    :meth:`process`, spending at most a wall-clock time budget per frame so a
    large backlog spreads across frames while the frame keeps rendering.
    Draining on the render thread keeps each callback's DearPyGui work on the
    thread that owns the context.

    A callback becomes due once the frame counter reaches its target frame;
    callbacks posted with a delay wait in the heap until then. Ordering within a
    frame follows the callback priority and then insertion order. Individual
    failures are caught and logged so the remaining callbacks still run.

    Non-instantiable by design: it is a shared execution channel reached
    through its class methods.
    """

    _callbacks: ClassVar[List[CallbackTask]] = []
    _lock: ClassVar[threading.Lock] = threading.Lock()
    _frame_counter: ClassVar[int] = 0
    _insertion_counter: ClassVar[int] = 0
    _stopped: ClassVar[bool] = False

    @classmethod
    def start(cls) -> None:
        """Mark the queue live for a fresh application run.

        Clears the stopped flag set by a previous :meth:`stop` so pending work
        drains again. Leaves the heap intact, because panels enqueue their first
        tree-build tasks during window construction, before the run loop starts
        draining.
        """
        with cls._lock:
            cls._stopped = False

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
    def notify_frame(cls) -> None:
        with cls._lock:
            cls._frame_counter += 1

    @classmethod
    def process(cls, budget_seconds: float) -> None:
        """Run the callbacks due at the current frame, up to a time budget.

        Drains callbacks whose target frame has been reached, newest-priority
        first, until either none remain due or the wall-clock budget is spent;
        callbacks left over are revisited on the next frame. At least one due
        callback runs per call, so even a tight budget makes forward progress.
        """
        deadline = time.perf_counter() + budget_seconds
        while True:
            with cls._lock:
                if cls._stopped:
                    return

                if not cls._callbacks or cls._callbacks[0].priority.frame > cls._frame_counter:
                    return

                task = heapq.heappop(cls._callbacks)
                frame_counter = cls._frame_counter

            assert task.priority.frame <= frame_counter, (
                "CallbackQueue drained a task ahead of its target frame; "
                "CallbackPriority.order must sort frame-first"
            )

            _, callback, args, kwargs = task
            if cls.run(callback, *args, **kwargs):
                cls.stop()
                return

            if time.perf_counter() >= deadline:
                return

    @classmethod
    def stop(cls) -> None:
        with cls._lock:
            cls._stopped = True
            cls._callbacks.clear()

    @classmethod
    def run(cls, callback: Callback, *args: Any, **kwargs: Any) -> bool:
        try:
            callback(*args, **kwargs)
            return False
        except CallbackQueueStop as exception:
            logger.error(f"Callback queue processing stopped due to the error: {exception}.")
            return True
        except Exception as exception:  # pylint: disable=broad-exception-caught
            logger.error_with_traceback(
                exception,
                f"Error executing callback {getattr(callback, '__name__', str(callback))}",
            )
            return False
