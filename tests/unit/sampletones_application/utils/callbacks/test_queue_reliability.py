from typing import List
from unittest.mock import patch

import pytest

from sampletones_application.utils.callbacks.queue import CallbackQueue

_real_queue_add = CallbackQueue.add

GENEROUS_BUDGET = 1.0
DRAIN_ONE_BUDGET = 0.0


@pytest.fixture(autouse=True)
def fresh_queue():
    """Give each test a clean, live CallbackQueue.

    CallbackQueue is a process-global singleton, so a prior test may leave tasks
    pending or the queue stopped. stop() clears the heap and marks it stopped,
    then start() marks it live again; teardown stops it. The add() patch pins the
    real heap-based add() over any call-through stub other suites install.
    """
    with patch.object(CallbackQueue, "add", _real_queue_add):
        CallbackQueue.stop()
        CallbackQueue.start()
        yield
        CallbackQueue.stop()


class TestCallbackQueueDelivery:
    def test_due_callback_is_delivered_by_process(self) -> None:
        fired: List[bool] = []

        CallbackQueue.add(lambda: fired.append(True))
        CallbackQueue.notify_frame()
        CallbackQueue.process(GENEROUS_BUDGET)

        assert fired == [True]

    def test_multiple_due_callbacks_all_delivered_in_insertion_order(self) -> None:
        results: List[int] = []

        for value in (1, 2, 3):
            CallbackQueue.add(lambda captured=value: results.append(captured))
        CallbackQueue.notify_frame()
        CallbackQueue.process(GENEROUS_BUDGET)

        assert results == [1, 2, 3]

    def test_lower_priority_number_runs_first(self) -> None:
        results: List[str] = []

        CallbackQueue.add(lambda: results.append("low_precedence"), priority=5)
        CallbackQueue.add(lambda: results.append("high_precedence"), priority=1)
        CallbackQueue.notify_frame()
        CallbackQueue.process(GENEROUS_BUDGET)

        assert results == ["high_precedence", "low_precedence"]

    def test_stop_discards_pending_callbacks(self) -> None:
        fired: List[bool] = []

        CallbackQueue.add(lambda: fired.append(True))
        CallbackQueue.stop()
        CallbackQueue.notify_frame()
        CallbackQueue.process(GENEROUS_BUDGET)

        assert fired == []

    def test_exception_in_callback_is_isolated(self) -> None:
        good_fired: List[bool] = []

        def bad_callback() -> None:
            raise RuntimeError("intentional error")

        CallbackQueue.add(bad_callback)
        CallbackQueue.add(lambda: good_fired.append(True))
        CallbackQueue.notify_frame()
        CallbackQueue.process(GENEROUS_BUDGET)

        assert good_fired == [True]

    def test_base_exception_propagates_out_of_process(self) -> None:
        """run() catches Exception but not BaseException, so a SystemExit raised in
        a callback propagates out of process() into the render loop rather than
        being swallowed, and aborts the current drain.
        """
        good_fired: List[bool] = []

        def base_exception_callback() -> None:
            raise SystemExit(0)

        CallbackQueue.add(base_exception_callback)
        CallbackQueue.add(lambda: good_fired.append(True))
        CallbackQueue.notify_frame()

        with pytest.raises(SystemExit):
            CallbackQueue.process(GENEROUS_BUDGET)

        assert good_fired == []


class TestCallbackQueueFrameDelay:
    def test_delayed_callback_is_not_due_before_its_frame(self) -> None:
        fired: List[bool] = []

        CallbackQueue.add(lambda: fired.append(True), delay=1)
        CallbackQueue.process(GENEROUS_BUDGET)

        assert fired == []

    def test_delayed_callback_becomes_due_after_frame_tick(self) -> None:
        fired: List[bool] = []

        CallbackQueue.add(lambda: fired.append(True), delay=1)
        CallbackQueue.notify_frame()
        CallbackQueue.process(GENEROUS_BUDGET)

        assert fired == [True]

    def test_zero_delay_callback_is_due_at_current_frame(self) -> None:
        fired: List[bool] = []

        CallbackQueue.add(lambda: fired.append(True), delay=0)
        CallbackQueue.process(GENEROUS_BUDGET)

        assert fired == [True]


class TestCallbackQueueBudget:
    def test_zero_budget_runs_one_due_callback_per_call(self) -> None:
        results: List[int] = []

        for value in (1, 2, 3):
            CallbackQueue.add(lambda captured=value: results.append(captured))
        CallbackQueue.notify_frame()

        CallbackQueue.process(DRAIN_ONE_BUDGET)
        assert results == [1]
        CallbackQueue.process(DRAIN_ONE_BUDGET)
        assert results == [1, 2]
        CallbackQueue.process(GENEROUS_BUDGET)
        assert results == [1, 2, 3]

    def test_not_yet_due_callbacks_survive_a_drain(self) -> None:
        results: List[str] = []

        CallbackQueue.add(lambda: results.append("now"), delay=0)
        CallbackQueue.add(lambda: results.append("later"), delay=2)
        CallbackQueue.notify_frame()
        CallbackQueue.process(GENEROUS_BUDGET)
        assert results == ["now"]

        CallbackQueue.notify_frame()
        CallbackQueue.process(GENEROUS_BUDGET)
        assert results == ["now", "later"]
