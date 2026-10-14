from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_shared.types.callback import VoidCallback


class RenderThreadCrossing:
    """Carries a playback's reports from the audio thread that makes them to the render thread, in their order.

    Every report waits in the callback queue at one priority, so a drain hands each one over in the order
    the output made it, and the end report lands after every position.
    """

    def __init__(self, *, priority: int) -> None:
        self._priority = priority

    def __call__(self, delivery: VoidCallback) -> None:
        CallbackQueue.add(delivery, priority=self._priority)
