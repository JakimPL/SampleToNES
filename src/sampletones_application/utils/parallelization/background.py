from typing import Final

from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor

SHUTDOWN_JOIN_TIMEOUT: Final[float] = 5.0


def stop_background_workers(timeout: float = SHUTDOWN_JOIN_TIMEOUT) -> None:
    """Wind down all background work before tearing down shared resources.

    The callback queue worker and the concurrent executors both touch
    non-thread-safe state (e.g. the dearpygui context), so they must be stopped
    and awaited together before that state is destroyed.
    """
    CallbackQueue.stop()
    SingleThreadExecutor.join_all(timeout=timeout)
