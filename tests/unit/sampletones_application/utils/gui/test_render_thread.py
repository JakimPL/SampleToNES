import threading
from typing import List

import pytest

from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.gui.render_thread import (
    claim_render_thread,
    is_render_thread,
    on_render_thread,
    release_render_thread,
)


@pytest.fixture
def unclaimed() -> None:
    """A context no run has claimed, over a queue live enough to drain what reaches it."""
    release_render_thread()
    CallbackQueue.start()


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

    def test_a_run_lets_the_thread_go(self, unclaimed: None) -> None:
        claim_render_thread()
        release_render_thread()

        assert is_render_thread() is True
