from typing import Any, Final, Iterator, List, Tuple
from unittest.mock import patch

import pytest

from sampletones_application.layout.behavior.scheduling.delays import SchedulingDelays
from sampletones_application.layout.behavior.scheduling.emit import SchedulingEmit
from sampletones_application.layout.behavior.scheduling.priorities import (
    SchedulingPriorities,
)
from sampletones_application.layout.behavior.scheduling.scheduling import (
    SchedulingBehavior,
)
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_shared.types.callback import Callback, VoidCallback

REAL_QUEUE_ADD: Final = CallbackQueue.add
FRAME_BUDGET_SECONDS: Final[float] = 1.0
DELAY_CLOCK: Final[str] = "sampletones_application.utils.callbacks.delay.time.monotonic"
CLOCK_START: Final[float] = 100.0


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
    """Scheduling behavior with every delay collapsed to zero for deterministic tests."""
    return SchedulingBehavior(
        delays=SchedulingDelays(
            schedule=0,
            reconstruction_update=0,
            cancel=0,
        ),
        priorities=SchedulingPriorities(
            update_status=0,
            gui_action=0,
            schedule=0,
        ),
        emit=SchedulingEmit(priority=0, batch_size=128),
        queue_budget_seconds=0.005,
    )


class HeldQueue:
    """The render loop's queue, holding what another thread hands over until a case drains it."""

    def __init__(self) -> None:
        self._held: List[Tuple[Callback, Tuple[Any, ...]]] = []

    def add(self, callback: Callback, *args: Any, **_scheduling: Any) -> None:
        self._held.append((callback, args))

    @property
    def held(self) -> int:
        """How many callbacks stand queued."""
        return len(self._held)

    def drain(self) -> None:
        """Runs what stands queued in the order it arrived, along with what running it queues."""
        while self._held:
            callback, args = self._held.pop(0)
            callback(*args)


@pytest.fixture
def held_queue(monkeypatch: pytest.MonkeyPatch) -> HeldQueue:
    """``CallbackQueue.add`` holding each callback until the case drains the queue."""
    queue = HeldQueue()
    monkeypatch.setattr(CallbackQueue, "add", queue.add)
    return queue


@pytest.fixture
def live_queue() -> Iterator[None]:
    """The real ``CallbackQueue``, live and empty for the case and stopped once it ends.

    The queue belongs to the whole process, so a case before this one may leave work pending or the
    queue stopped. The real ``add`` is pinned over the call-through ``synchronous_queue`` installs,
    so what a case queues waits for a drain the way it does in the render loop.
    """
    with patch.object(CallbackQueue, "add", REAL_QUEUE_ADD):
        CallbackQueue.stop()
        CallbackQueue.start()
        yield
        CallbackQueue.stop()


def draw_frame() -> None:
    """One frame of the render loop as the queue meets it: the count moves on, then the drain."""
    CallbackQueue.notify_frame()
    CallbackQueue.process(FRAME_BUDGET_SECONDS)


class ManualClock:
    """The monotonic clock a wait on the render thread reads, moved by the case alone."""

    def __init__(self, now: float) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def delay_clock(monkeypatch: pytest.MonkeyPatch) -> ManualClock:
    """The clock ``call_after`` measures its wait by, standing still until the case moves it."""
    clock = ManualClock(CLOCK_START)
    monkeypatch.setattr(DELAY_CLOCK, clock)
    return clock
