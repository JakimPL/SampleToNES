import time
from typing import Final

from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_shared.types.callback import VoidCallback

NEXT_FRAME: Final[int] = 1


def call_after(seconds: float, callback: VoidCallback) -> None:
    """Runs ``callback`` on the render thread once ``seconds`` have passed.

    The wait is read against the clock at each frame's drain, so it lasts the same span at any frame
    rate, and the callback runs on the thread that owns the widgets it reaches. The wait travels
    through the queue, so the shutdown that stops the queue drops a wait still under way.
    """
    deadline = time.monotonic() + seconds
    CallbackQueue.add(_call_when_due, deadline, callback, delay=NEXT_FRAME)


def _call_when_due(deadline: float, callback: VoidCallback) -> None:
    if time.monotonic() < deadline:
        CallbackQueue.add(_call_when_due, deadline, callback, delay=NEXT_FRAME)
        return

    callback()
