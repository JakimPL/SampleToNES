import threading
from typing import Any, Optional

from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_shared.types.callback import Callback

_render_thread: Optional[int] = None


def claim_render_thread() -> None:
    """Names the thread DearPyGui's context belongs to, which is the one drawing the frames."""
    global _render_thread  # pylint: disable=global-statement
    _render_thread = threading.get_ident()


def release_render_thread() -> None:
    """Lets the render thread go, which a run does once its loop has stopped."""
    global _render_thread  # pylint: disable=global-statement
    _render_thread = None


def is_render_thread() -> bool:
    """Whether the caller stands where DearPyGui's context is.

    A run claims the thread when its loop starts and lets it go when the loop stops, so before and
    after that — while the interface is being built, and while it is being taken down — whichever
    thread is asking is the one holding the context.
    """
    return _render_thread is None or threading.get_ident() == _render_thread


def on_render_thread(
    work: Callback,
    *args: Any,
    priority: int = 0,
    **kwargs: Any,
) -> None:
    """Runs ``work`` where DearPyGui's context belongs: the thread drawing the frames.

    DearPyGui invokes a widget's callback on a thread of its own, so a panel that rebuilds itself
    straight from a gesture creates and drops widgets while the render thread walks them, and a
    callback freed there is freed with no Python thread state — a crash rather than a glitch. Work
    already on the render thread runs where it stands; work arriving from any other thread joins
    the queue the render loop drains, so it lands between frames.

    A callback that reads a value or sets one on a standing widget runs where it is called; one
    that creates or deletes items comes through here.
    """
    if is_render_thread():
        work(*args, **kwargs)
        return

    CallbackQueue.add(work, *args, priority=priority, **kwargs)
