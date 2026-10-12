import threading
from functools import partial
from typing import Callable, Generic, Optional, ParamSpec

from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_shared.types.callback import VoidCallback

ReportParameters = ParamSpec("ReportParameters")


class LatestDelivery(Generic[ReportParameters]):
    """Carries a run's reports to the render thread, where the newest one stands for those before it.

    A run reports where it stands as often as it moves, from whichever thread moves it, and each
    report states the whole of that reading. One delivery therefore waits in the queue at a time,
    and the drain that reaches it hands ``handler`` the newest report filed. A run filing thousands
    of reports between two frames costs the render thread one handling per drain.

    The delivery takes its place in the queue with the first report it carries, so whatever is
    posted after that report, such as the run's outcome, still runs after it.
    """

    def __init__(
        self,
        handler: Callable[ReportParameters, None],
        *,
        priority: int,
    ) -> None:
        """Holds the handler the newest report reaches.

        Args:
            handler: What takes a report on the render thread.
            priority: The priority the delivery waits in the queue at, which the run's other
                results share so they keep their order.
        """
        self._handler = handler
        self._priority = priority
        self._lock = threading.Lock()
        self._newest: Optional[VoidCallback] = None

    def post(
        self,
        *args: ReportParameters.args,
        **kwargs: ReportParameters.kwargs,
    ) -> None:
        """Files a report from any thread, which supersedes a report still waiting for the render thread."""
        with self._lock:
            waiting = self._newest is not None
            self._newest = partial(self._handler, *args, **kwargs)

        if not waiting:
            CallbackQueue.add(self._deliver, priority=self._priority)

    def _deliver(self) -> None:
        with self._lock:
            newest, self._newest = self._newest, None

        if newest is not None:
            newest()
