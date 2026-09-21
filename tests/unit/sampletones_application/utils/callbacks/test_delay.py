import threading
from dataclasses import dataclass
from typing import Final, List

import pytest

from sampletones_application.utils.callbacks.delay import call_after
from sampletones_application.utils.callbacks.queue import CallbackQueue
from tests.suite.application import ManualClock, draw_frame
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

WAIT_SECONDS: Final[float] = 1.0
SHORT_OF_THE_WAIT: Final[float] = 0.999
FRAMES_AFTER: Final[int] = 5


class Calls:
    """The threads a callback ran on, one entry per run."""

    def __init__(self) -> None:
        self.threads: List[threading.Thread] = []

    def __call__(self) -> None:
        self.threads.append(threading.current_thread())


@pytest.mark.usefixtures("live_queue")
class TestTheWaitRunsOnTheRenderThread(BaseTestSuite):
    """A wait handed to ``call_after`` ends in one call, made by the thread draining the queue."""

    def test_nothing_runs_while_the_wait_stands(self, delay_clock: ManualClock) -> None:
        calls = Calls()

        call_after(WAIT_SECONDS, calls)
        delay_clock.advance(SHORT_OF_THE_WAIT)
        draw_frame()

        assert calls.threads == []

    def test_the_first_frame_after_the_wait_runs_it_once(self, delay_clock: ManualClock) -> None:
        calls = Calls()

        call_after(WAIT_SECONDS, calls)
        delay_clock.advance(WAIT_SECONDS)
        for _ in range(FRAMES_AFTER):
            draw_frame()

        assert calls.threads == [threading.current_thread()]

    def test_the_wait_starts_no_thread(self, delay_clock: ManualClock) -> None:
        standing = set(threading.enumerate())

        call_after(WAIT_SECONDS, Calls())

        assert set(threading.enumerate()) == standing

    def test_a_stopped_queue_drops_the_wait(self, delay_clock: ManualClock) -> None:
        """The shutdown stops the queue before the context goes, so a wait under way never lands."""
        calls = Calls()

        call_after(WAIT_SECONDS, calls)
        CallbackQueue.stop()
        delay_clock.advance(WAIT_SECONDS)
        CallbackQueue.start()
        for _ in range(FRAMES_AFTER):
            draw_frame()

        assert calls.threads == []


@pytest.mark.usefixtures("live_queue")
class TestTheWaitLastsTheSameSpanAtAnyFrameRate(BaseTestSuite):
    """The frame rate is the reader's to set, so the wait is read against the clock."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        frames_during_the_wait: int

    test_cases = (
        TestCase(label="one_frame", frames_during_the_wait=1),
        TestCase(label="a_frame_rate_limited_display", frames_during_the_wait=60),
        TestCase(label="an_unlimited_frame_rate", frames_during_the_wait=2000),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_it_runs_once_the_clock_reaches_the_end(
        self,
        test_case: TestCase,
        delay_clock: ManualClock,
    ) -> None:
        calls = Calls()
        step = SHORT_OF_THE_WAIT / test_case.frames_during_the_wait

        call_after(WAIT_SECONDS, calls)
        for _ in range(test_case.frames_during_the_wait):
            delay_clock.advance(step)
            draw_frame()

        assert calls.threads == []

        delay_clock.advance(WAIT_SECONDS)
        draw_frame()

        assert len(calls.threads) == 1
