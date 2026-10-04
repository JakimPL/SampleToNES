import threading
from typing import Callable, List

import pytest

from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.gui.render_thread import (
    claim_render_thread,
    is_render_thread,
    on_render_thread,
    release_render_thread,
    reset_render_thread,
)


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
