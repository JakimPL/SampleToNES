import threading
import time
from typing import Callable, List
from unittest.mock import patch

import pytest

from sampletones_application.utils.callbacks.failures import UnhandledFailures
from sampletones_application.utils.parallelization.coalescing import LatestWinsExecutor


def _wait_until(predicate: Callable[[], bool], timeout: float = 1.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


@pytest.fixture
def reported() -> List[Exception]:
    """The failures the channel shows, presented on the thread that reports them."""
    failures: List[Exception] = []
    UnhandledFailures.attach(failures.append, post=lambda present, exception: present(exception))
    return failures


class TestLatestWinsExecutor:
    def test_runs_a_submitted_task(self) -> None:
        executor = LatestWinsExecutor()
        done = threading.Event()

        executor.submit(done.set)

        assert done.wait(1.0)

    def test_is_running_is_false_when_idle(self) -> None:
        executor = LatestWinsExecutor()

        assert executor.is_running is False

    def test_reports_running_during_a_task_then_idle(self) -> None:
        executor = LatestWinsExecutor()
        started = threading.Event()
        release = threading.Event()

        def task() -> None:
            started.set()
            release.wait(1.0)

        executor.submit(task)
        assert started.wait(1.0)
        assert executor.is_running is True

        release.set()
        assert _wait_until(lambda: executor.is_running is False)

    def test_submit_while_busy_is_accepted(self) -> None:
        executor = LatestWinsExecutor()
        started = threading.Event()
        release = threading.Event()

        def blocking() -> None:
            started.set()
            release.wait(1.0)

        first = executor.submit(blocking)
        assert started.wait(1.0)
        second = executor.submit(lambda: None)
        release.set()

        assert first is True
        assert second is True

    def test_coalesces_a_burst_to_the_latest(self) -> None:
        executor = LatestWinsExecutor()
        ran: List[str] = []
        first_started = threading.Event()
        release = threading.Event()
        done = threading.Event()

        def first() -> None:
            ran.append("a")
            first_started.set()
            release.wait(1.0)

        def middle() -> None:
            ran.append("b")

        def last() -> None:
            ran.append("c")
            done.set()

        executor.submit(first)
        assert first_started.wait(1.0)

        executor.submit(middle)
        executor.submit(last)

        release.set()
        assert done.wait(1.0)
        assert ran == ["a", "c"]

    def test_launch_failure_reports_false_and_stays_idle(self) -> None:
        executor = LatestWinsExecutor()

        with patch.object(executor._executor, "execute", return_value=False):
            accepted = executor.submit(lambda: None)

        assert accepted is False
        assert executor.is_running is False


class TestAFailingTask:
    """A task that fails is reported, and the worker goes on serving what is submitted."""

    def test_a_failing_task_is_reported_and_a_later_one_runs(self, reported: List[Exception]) -> None:
        executor = LatestWinsExecutor()
        failure = RuntimeError("the task went wrong")
        done = threading.Event()

        def failing() -> None:
            raise failure

        executor.submit(failing)
        assert _wait_until(lambda: executor.is_running is False)
        executor.submit(done.set)

        assert done.wait(1.0)
        assert reported == [failure]
        assert _wait_until(lambda: executor.is_running is False)

    def test_a_task_submitted_while_one_fails_runs_after_it(self, reported: List[Exception]) -> None:
        executor = LatestWinsExecutor()
        started = threading.Event()
        release = threading.Event()
        done = threading.Event()

        def failing() -> None:
            started.set()
            release.wait(1.0)
            raise RuntimeError("the task went wrong")

        executor.submit(failing)
        assert started.wait(1.0)
        executor.submit(done.set)
        release.set()

        assert done.wait(1.0)
        assert len(reported) == 1
