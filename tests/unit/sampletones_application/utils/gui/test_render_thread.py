import threading
from dataclasses import dataclass, field
from typing import Callable, Final, Iterator, List
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.gui.render_thread import (
    answered_while_drawing,
    claim_render_thread,
    is_render_thread,
    on_render_thread,
    release_render_thread,
    reset_render_thread,
)

ANSWER: Final[str] = "the reader answered"
WAITING_TIMEOUT: Final[float] = 5.0


@pytest.fixture
def unclaimed() -> None:
    """A context no run has claimed, over a queue live enough to drain what reaches it."""
    reset_render_thread()
    CallbackQueue.start()


def from_another_thread(work: Callable[[], None]) -> None:
    """Runs ``work`` on a thread of its own and waits for it, the way a worker reaches the interface."""
    worker = threading.Thread(target=work)
    worker.start()
    worker.join()


@dataclass
class Frames:
    """The frames a waiting draws, counted, and the moment it draws the first of them."""

    drawn: List[int] = field(default_factory=list)
    first: threading.Event = field(default_factory=threading.Event)


@pytest.fixture(name="frames")
def frames_fixture(unclaimed: None) -> Iterator[Frames]:
    """A loop drawing on the test's thread, each frame counted where DearPyGui would draw it.

    The thread claims the frames the way a running interface does. A suite has no context to draw
    in, so DearPyGui's two calls are stood in for, and each frame drawn is a count.
    """
    frames = Frames()

    def frame() -> None:
        frames.drawn.append(len(frames.drawn))
        frames.first.set()

    claim_render_thread()
    with (
        patch.object(dpg, "is_dearpygui_running", return_value=True),
        patch.object(dpg, "render_dearpygui_frame", side_effect=frame),
    ):
        yield frames


class TestWhereWorkRuns:
    """Work that creates or deletes widgets belongs on the thread holding DearPyGui's context."""

    def test_an_unclaimed_context_runs_where_it_stands(self, unclaimed: None) -> None:
        ran: List[str] = []

        on_render_thread(ran.append, "built")

        assert ran == ["built"]

    def test_the_thread_a_run_claimed_runs_where_it_stands(self, unclaimed: None) -> None:
        ran: List[str] = []
        claim_render_thread()
        try:
            on_render_thread(ran.append, "drawn")
        finally:
            release_render_thread()

        assert ran == ["drawn"]

    def test_another_thread_joins_the_queue_the_loop_drains(self, unclaimed: None) -> None:
        ran: List[str] = []
        claim_render_thread()
        worker = threading.Thread(target=on_render_thread, args=(ran.append, "gestured"))
        try:
            worker.start()
            worker.join()

            assert ran == []
            CallbackQueue.process(1.0)
        finally:
            release_render_thread()

        assert ran == ["gestured"]


class TestAfterTheLoopStopped:
    """Once a run's loop stops, the thread that drew keeps the context until the context is destroyed.

    The teardown runs on that thread, so its work runs where it stands. A worker's late work joins the
    queue, which the teardown stops, so it never reaches a context that is going or gone.
    """

    def test_the_thread_that_drew_still_holds_the_context(self, unclaimed: None) -> None:
        ran: List[str] = []
        claim_render_thread()
        release_render_thread()

        on_render_thread(ran.append, "taken down")

        assert is_render_thread() is True
        assert ran == ["taken down"]

    def test_another_thread_holds_no_context(self, unclaimed: None) -> None:
        answers: List[bool] = []
        claim_render_thread()
        release_render_thread()

        from_another_thread(lambda: answers.append(is_render_thread()))

        assert answers == [False]

    def test_a_late_worker_s_work_is_let_go_with_the_stopped_queue(self, unclaimed: None) -> None:
        ran: List[str] = []
        claim_render_thread()
        release_render_thread()
        CallbackQueue.stop()

        from_another_thread(lambda: on_render_thread(ran.append, "late"))
        CallbackQueue.process(1.0)

        assert ran == []

    def test_a_run_taken_down_before_it_drew_leaves_the_context_to_its_teardown(self, unclaimed: None) -> None:
        answers: List[bool] = []

        release_render_thread()
        from_another_thread(lambda: answers.append(is_render_thread()))

        assert is_render_thread() is True
        assert answers == [False]

    def test_a_fresh_context_is_built_by_whichever_thread_asks(self, unclaimed: None) -> None:
        answers: List[bool] = []
        claim_render_thread()
        release_render_thread()

        reset_render_thread()
        from_another_thread(lambda: answers.append(is_render_thread()))

        assert answers == [True]


class TestAGestureThatWaits:
    """A gesture on the thread drawing the frames holds them up, so its waiting draws them meanwhile.

    The cases that wait for a drawn frame before answering take the loop whichever way the threads
    are scheduled.
    """

    def test_it_reports_what_the_waiting_answered(self, frames: Frames) -> None:
        assert answered_while_drawing(lambda: ANSWER) == ANSWER

    def test_it_draws_while_the_waiting_stands(self, frames: Frames) -> None:
        def answer() -> str:
            frames.first.wait(WAITING_TIMEOUT)
            return ANSWER

        assert answered_while_drawing(answer) == ANSWER
        assert frames.drawn

    def test_a_failure_reaches_the_gesture_that_waited(self, frames: Frames) -> None:
        def failing() -> str:
            frames.first.wait(WAITING_TIMEOUT)
            raise RuntimeError("the dialog went wrong")

        with pytest.raises(RuntimeError):
            answered_while_drawing(failing)

        assert frames.drawn


class TestAWaitingWithNoFramesToDraw:
    """Work asked where no loop draws its frames runs where it stands, on the thread that asked.

    The work answers the thread it ran on. These cases leave DearPyGui as it is, since a suite holds
    no context for a frame.
    """

    def test_work_from_another_thread_runs_on_it(self, frames: Frames) -> None:
        on_the_asking_thread: List[bool] = []

        from_another_thread(
            lambda: on_the_asking_thread.append(answered_while_drawing(threading.get_ident) == threading.get_ident())
        )

        assert on_the_asking_thread == [True]
        assert not frames.drawn

    def test_work_before_the_loop_draws_runs_where_it_stands(self, unclaimed: None) -> None:
        assert answered_while_drawing(threading.get_ident) == threading.get_ident()

    def test_work_after_the_loop_stopped_runs_where_it_stands(self, unclaimed: None) -> None:
        claim_render_thread()
        release_render_thread()

        assert answered_while_drawing(threading.get_ident) == threading.get_ident()
