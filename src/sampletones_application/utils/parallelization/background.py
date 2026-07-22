from typing import Final

from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor

SHUTDOWN_JOIN_TIMEOUT: Final[float] = 5.0


def stop_background_workers(timeout: float = SHUTDOWN_JOIN_TIMEOUT) -> None:
    """Wind down all background work before tearing down shared resources.

    The shutdown is requested first so any in-flight task unwinds at its next
    cancellation point, letting the join return promptly. Stopping the callback
    queue then discards any results still pending delivery to the main thread, and
    the concurrent executor threads touch the dearpygui context, so both are halted
    and awaited before that context is destroyed.
    """
    SingleThreadExecutor.request_shutdown()
    CallbackQueue.stop()
    SingleThreadExecutor.join_all(timeout=timeout)
