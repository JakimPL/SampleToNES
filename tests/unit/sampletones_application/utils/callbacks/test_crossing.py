import threading
from functools import partial
from typing import Final, List

import pytest

from sampletones_application.utils.callbacks.crossing import RenderThreadCrossing
from sampletones_application.utils.callbacks.priority import DEFAULT_PRIORITY
from tests.suite.application import draw_frame
from tests.suite.base import BaseTestSuite

REPORTS: Final[int] = 1_000
END: Final[int] = -1


class Deliveries:
    """Every report a crossing handed over, and the thread it ran on."""

    def __init__(self) -> None:
        self.reports: List[int] = []
        self.threads: List[threading.Thread] = []

    def deliver(self, report: int) -> None:
        self.reports.append(report)
        self.threads.append(threading.current_thread())


@pytest.fixture
def crossing() -> RenderThreadCrossing:
    return RenderThreadCrossing(priority=DEFAULT_PRIORITY)


@pytest.fixture
def deliveries() -> Deliveries:
    return Deliveries()


@pytest.mark.usefixtures("live_queue")
class TestReportsCrossToTheRenderThread(BaseTestSuite):
    """A report an audio thread posts waits for the render thread's drain, and every one lands in its order."""

    def test_a_report_from_an_audio_thread_waits_for_the_drain(
        self,
        crossing: RenderThreadCrossing,
        deliveries: Deliveries,
    ) -> None:
        writer = threading.Thread(target=crossing, args=(partial(deliveries.deliver, 1),))
        writer.start()
        writer.join()
        waiting = list(deliveries.reports)

        draw_frame()

        assert waiting == []
        assert deliveries.reports == [1]
        assert deliveries.threads == [threading.current_thread()]

    def test_every_report_lands_in_the_order_posted_with_the_end_last(
        self,
        crossing: RenderThreadCrossing,
        deliveries: Deliveries,
    ) -> None:
        for report in range(REPORTS):
            crossing(partial(deliveries.deliver, report))
        crossing(partial(deliveries.deliver, END))

        draw_frame()

        assert deliveries.reports == [*range(REPORTS), END]
