from unittest.mock import patch

import pytest

from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.thread import SingleThreadExecutor


@pytest.fixture(autouse=True)
def synchronous_queue():
    """Replace CallbackQueue.add with a direct call-through.

    Makes _emit() synchronous so tests do not need a running queue worker thread.
    CallbackQueue.add signature: add(callback, *args, priority=0, delay=0, **kwargs)
    """
    with patch.object(
        CallbackQueue,
        "add",
        side_effect=lambda callback, *args, priority=0, delay=0, **kwargs: callback(*args),
    ):
        yield


@pytest.fixture(autouse=True)
def synchronous_executor():
    """Replace SingleThreadExecutor.execute with a synchronous call.

    Makes background tasks run inline so tests remain deterministic without
    threading.Event barriers. Tests that specifically verify debounce or
    non-preemptive cancellation must override this fixture locally.
    """

    def execute_sync(self: SingleThreadExecutor, target, wait: bool = True) -> bool:
        target()
        return True

    with patch.object(SingleThreadExecutor, "execute", execute_sync):
        yield
