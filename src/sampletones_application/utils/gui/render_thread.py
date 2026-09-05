import threading
from typing import Any, Optional

from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_shared.types.callback import Callback

_RENDER_THREAD: Optional[int] = None


def claim_render_thread() -> None:
    """Names the thread DearPyGui's context belongs to, which is the one drawing the frames."""
    global _RENDER_THREAD  # pylint: disable=global-statement
    _RENDER_THREAD = threading.get_ident()


def release_render_thread() -> None:
    """Lets the render thread go, which a run does once its loop has stopped."""
    global _RENDER_THREAD  # pylint: disable=global-statement
    _RENDER_THREAD = None


def is_render_thread() -> bool:
    """Whether the caller stands where DearPyGui's context is.

    A run claims the thread when its loop starts and lets it go when the loop stops, so before and
    after that — while the interface is being built, and while it is being taken down — whichever
    thread is asking is the one holding the context.
    """
    return _RENDER_THREAD is None or threading.get_ident() == _RENDER_THREAD


def on_render_thread(
    work: Callback,
    *args: Any,
    priority: int = 0,
    **kwargs: Any,
) -> None:
    """Runs ``work`` where DearPyGui's context belongs: the thread drawing the frames.

    A worker of our own reaches the interface while the render thread is walking the very items it
    would create and drop, and an item freed there is freed with no Python thread state — a crash
    rather than a glitch. Work already on the render thread runs where it stands; work arriving
    from any other thread joins the queue the render loop drains, so it lands between frames.

    A widget's own callback runs on the render thread, since DearPyGui calls it inside the frame
    being drawn, and reaches this as a direct call.
    """
    if is_render_thread():
        work(*args, **kwargs)
        return

    CallbackQueue.add(work, *args, priority=priority, **kwargs)
