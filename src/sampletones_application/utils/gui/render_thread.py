import threading
import time
from concurrent.futures import ThreadPoolExecutor
from enum import Enum, auto
from typing import Any, Callable, Final, Optional, TypeVar

import dearpygui.dearpygui as dpg

from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_shared.types.callback import Callback

AnswerT = TypeVar("AnswerT")

FRAME_PAUSE: Final[float] = 1 / 60


class RenderPhase(Enum):
    """Where a run stands with DearPyGui's context, which decides the thread work runs on."""

    BUILDING = auto()
    DRAWING = auto()
    STOPPED = auto()


_PHASE: RenderPhase = RenderPhase.BUILDING
_RENDER_THREAD: Optional[int] = None


def reset_render_thread() -> None:
    """Hands a fresh context to whichever thread asks, the state a new interface is built in."""
    global _PHASE, _RENDER_THREAD  # pylint: disable=global-statement
    _PHASE = RenderPhase.BUILDING
    _RENDER_THREAD = None


def claim_render_thread() -> None:
    """Names the thread DearPyGui's context belongs to, which is the one drawing the frames."""
    global _PHASE, _RENDER_THREAD  # pylint: disable=global-statement
    _PHASE = RenderPhase.DRAWING
    _RENDER_THREAD = threading.get_ident()


def release_render_thread() -> None:
    """Marks the loop as stopped, which a run does as its teardown begins.

    The thread that ran the loop keeps the context until it is destroyed, since the teardown runs
    there. Work from any other thread joins the queue, which the teardown stops, so the queue lets it go.
    A run taken down before its loop claimed a thread leaves the context to the thread taking it
    down.
    """
    global _PHASE, _RENDER_THREAD  # pylint: disable=global-statement
    _PHASE = RenderPhase.STOPPED
    if _RENDER_THREAD is None:
        _RENDER_THREAD = threading.get_ident()


def is_render_thread() -> bool:
    """Whether the caller stands where DearPyGui's context is.

    While the interface is being built, no run has claimed the thread, and whichever thread is
    asking is the one holding the context. Once a run claims the thread, it holds the context for
    as long as the context lasts: while the loop draws, and while the run is taken down after it.
    """
    match _PHASE:
        case RenderPhase.BUILDING:
            return True
        case RenderPhase.DRAWING | RenderPhase.STOPPED:
            return threading.get_ident() == _RENDER_THREAD


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
    from any other thread joins the queue the render loop drains, so it lands between frames. Once
    the loop has stopped, that queue is stopped too, so a worker's late work is let go of.

    A widget's own callback reaches this as a direct call, since DearPyGui gathers it for the
    frame to run rather than answering the gesture on a thread of its own.
    """
    if is_render_thread():
        work(*args, **kwargs)
        return

    CallbackQueue.add(work, *args, priority=priority, **kwargs)


def answered_while_drawing(work: Callable[[], AnswerT]) -> AnswerT:
    """Run ``work`` beside the frames rather than in place of them, and report what it answers.

    A native dialog answers when the reader does, which is as long as they take. Standing on the
    render thread for that leaves the window with nothing drawing it, so the work goes to a thread
    of its own and the frames keep being drawn until it reports back. The gestures those frames
    gather wait for the drain that follows, so the interface stays painted while it stands inert —
    which is what a dialog standing in front of it means.

    Work reached from any other thread runs where it stands, since nothing there holds the frames.
    """
    if not is_render_thread():
        return work()

    with ThreadPoolExecutor(max_workers=1) as pool:
        answer = pool.submit(work)
        while not answer.done() and dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
            time.sleep(FRAME_PAUSE)

        return answer.result()
