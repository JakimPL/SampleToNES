import threading
from typing import Callable

from sampletones_application.utils.callbacks.queue import CallbackQueue


class QueueRenderThread:
    """SampleToNES's render thread, reached through the queue its own workers post to.

    The queue drains between frames on the thread drawing them, which is where every DearPyGui call
    belongs, and it counts a delay in frames drawn.
    """

    def __init__(self) -> None:
        self._running = threading.Event()
        self._stopped = threading.Event()

    def post(
        self,
        task: Callable[[], None],
        *,
        frames: int,
    ) -> None:
        """Queues ``task`` to run on the render thread once ``frames`` frames are drawn."""
        CallbackQueue.add(task, delay=frames)

    def is_running(self) -> bool:
        """Whether the loop is drawing."""
        return self._running.is_set()

    def frames_drawn(self) -> int:
        """How many frames the loop has drawn, counted by the queue it drains."""
        return CallbackQueue.current_frame()

    def start(self) -> None:
        """Marks the loop as drawing, which is when posted work starts being answered."""
        self._running.set()

    def stop(self) -> None:
        """Marks the loop as stopped, so a question still waiting fails at once."""
        self._running.clear()
        self._stopped.set()

    def wait_stopped(self, timeout: float) -> bool:
        """Waits up to ``timeout`` seconds for the loop to stop, and says whether it did."""
        return self._stopped.wait(timeout)
