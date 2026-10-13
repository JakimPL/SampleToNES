import threading
from typing import Final, List, Union

import pytest

from sampletones_application.utils.callbacks.latest import LatestDelivery
from sampletones_application.utils.callbacks.priority import DEFAULT_PRIORITY
from sampletones_application.utils.callbacks.queue import CallbackQueue
from tests.suite.application import draw_frame
from tests.suite.base import BaseTestSuite

REPORTS: Final[int] = 1_000
WORKERS: Final[int] = 4
OUTCOME: Final[str] = "outcome"

Handled = List[Union[int, str]]


class Handler:
    """What a delivery hands over, and the threads it was handed over on."""

    def __init__(self) -> None:
        self.handled: Handled = []
        self.threads: List[threading.Thread] = []

    def __call__(self, report: int) -> None:
        self.handled.append(report)
        self.threads.append(threading.current_thread())


@pytest.fixture
def handler() -> Handler:
    return Handler()


@pytest.fixture
def delivery(handler: Handler) -> LatestDelivery[[int]]:
    return LatestDelivery(handler, priority=DEFAULT_PRIORITY)


@pytest.mark.usefixtures("live_queue")
class TestTheNewestReportStandsForTheRest(BaseTestSuite):
    """Reports filed between two drains reach the handler as the newest of them, once."""

    def test_nothing_is_handled_before_the_drain(self, delivery: LatestDelivery[[int]], handler: Handler) -> None:
        delivery.post(1)

        assert handler.handled == []

    def test_a_drain_hands_over_the_newest_report_alone(
        self,
        delivery: LatestDelivery[[int]],
        handler: Handler,
    ) -> None:
        for report in range(REPORTS):
            delivery.post(report)

        draw_frame()

        assert handler.handled == [REPORTS - 1]

    def test_a_report_after_a_drain_waits_for_the_next_one(
        self,
        delivery: LatestDelivery[[int]],
        handler: Handler,
    ) -> None:
        delivery.post(1)
        draw_frame()
        delivery.post(2)
        delivery.post(3)

        draw_frame()

        assert handler.handled == [1, 3]

    def test_a_drain_with_no_report_hands_nothing_over(
        self,
        delivery: LatestDelivery[[int]],
        handler: Handler,
    ) -> None:
        delivery.post(1)
        draw_frame()

        draw_frame()

        assert handler.handled == [1]


@pytest.mark.usefixtures("live_queue")
class TestTheReportKeepsItsPlaceInTheQueue(BaseTestSuite):
    """The delivery waits where its first report put it, so the run's other results keep their order."""

    def test_what_is_posted_after_a_report_runs_after_the_newest_one(
        self,
        delivery: LatestDelivery[[int]],
        handler: Handler,
    ) -> None:
        delivery.post(1)
        CallbackQueue.add(handler.handled.append, OUTCOME, priority=DEFAULT_PRIORITY)
        delivery.post(2)

        draw_frame()

        assert handler.handled == [2, OUTCOME]

    def test_what_is_posted_before_a_report_runs_before_it(
        self,
        delivery: LatestDelivery[[int]],
        handler: Handler,
    ) -> None:
        CallbackQueue.add(handler.handled.append, OUTCOME, priority=DEFAULT_PRIORITY)
        delivery.post(1)

        draw_frame()

        assert handler.handled == [OUTCOME, 1]


@pytest.mark.usefixtures("live_queue")
class TestReportsFromOtherThreads(BaseTestSuite):
    """Workers file reports from threads of their own, and the thread draining the queue hands one over."""

    def test_reports_from_several_workers_are_handled_once_on_the_draining_thread(
        self,
        delivery: LatestDelivery[[int]],
        handler: Handler,
    ) -> None:
        workers = [
            threading.Thread(target=lambda: [delivery.post(report) for report in range(REPORTS)])
            for _ in range(WORKERS)
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()

        draw_frame()

        assert handler.handled == [REPORTS - 1]
        assert handler.threads == [threading.current_thread()]
