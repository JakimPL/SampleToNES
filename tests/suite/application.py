from typing import Iterator
from unittest.mock import patch

import pytest

from sampletones_application.layout.behavior import SchedulingBehavior
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_shared.types.callback import VoidCallback


@pytest.fixture(autouse=True)
def synchronous_queue() -> Iterator[None]:
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
def synchronous_executor() -> Iterator[None]:
    """Replace SingleThreadExecutor.execute with a synchronous call.

    Makes background tasks run inline so tests remain deterministic without
    threading.Event barriers. Tests that specifically verify debounce or
    non-preemptive cancellation must override this fixture locally.
    """

    def execute_sync(self: SingleThreadExecutor, target: VoidCallback, wait: bool = True) -> bool:
        target()
        return True

    with patch.object(SingleThreadExecutor, "execute", execute_sync):
        yield


@pytest.fixture
def scheduling() -> SchedulingBehavior:
    """Scheduling behaviour with every delay collapsed to zero for deterministic tests."""
    return SchedulingBehavior(
        delay_gui_action=0,
        delay_schedule=0,
        delay_reconstruction_update=0,
        delay_cancel=0,
        priority_update_status=0,
        priority_gui_action=0,
        priority_schedule=0,
        priority_emit=0,
        queue_budget_seconds=0.005,
        emit_batch_size=128,
    )
