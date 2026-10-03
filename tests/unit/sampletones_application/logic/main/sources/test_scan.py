from pathlib import Path
from typing import Callable, Final, List, Optional, Tuple

import pytest

from sampletones_application.logic.main.sources.scan import FolderScan, ScanPhase
from sampletones_application.services.folder_scan.result import (
    FolderScanCanceled,
    FolderScanError,
    FolderScanProgress,
    FolderScanRequest,
    FolderScanResult,
    FolderScanStarted,
    FolderScanSuccess,
)

MANY: Final[Path] = Path("many")
FEW: Final[Path] = Path("few")
OTHER: Final[Path] = Path("other")
COUNT: Final[int] = 64
FOUND: Final[Tuple[Path, ...]] = (Path("few/a.wav"), Path("few/b.wav"))

Answered = List[Tuple[Path, Tuple[Path, ...]]]


class ScanServiceStandIn:
    """The walk a scan drives, its reports handed back by the case the way the render loop drains them."""

    def __init__(self) -> None:
        self.started: List[FolderScanRequest] = []
        self.stops = 0
        self._handler: Optional[Callable[[FolderScanResult], None]] = None

    def subscribe(self, handler: Callable[[FolderScanResult], None]) -> None:
        self._handler = handler

    def start(self, request: FolderScanRequest) -> None:
        self.started.append(request)

    def stop(self) -> None:
        self.stops += 1

    @property
    def latest(self) -> FolderScanRequest:
        return self.started[-1]

    def report(self, result: FolderScanResult) -> None:
        assert self._handler is not None
        self._handler(result)


class Heard:
    """What the reader is told: the folder named, the count, the reading given up, and a failure."""

    def __init__(self, scan: FolderScan) -> None:
        self.started: List[Path] = []
        self.counts: List[int] = []
        self.stopped = 0
        self.failures: List[Exception] = []
        scan.on_started = self.started.append
        scan.on_progress = self.counts.append
        scan.on_stopped = self._stop
        scan.on_failed = self.failures.append

    def _stop(self) -> None:
        self.stopped += 1


@pytest.fixture(name="service")
def service_fixture() -> ScanServiceStandIn:
    return ScanServiceStandIn()


@pytest.fixture(name="scan")
def scan_fixture(service: ScanServiceStandIn) -> FolderScan:
    return FolderScan(service)


@pytest.fixture(name="heard")
def heard_fixture(scan: FolderScan) -> Heard:
    return Heard(scan)


@pytest.fixture(name="answered")
def answered_fixture() -> Answered:
    return []


def answer_into(answered: Answered) -> Callable[[Path, Tuple[Path, ...]], None]:
    return lambda root, recordings: answered.append((root, recordings))


class TestAReading:
    """A folder asked for is read, and the reader is told what the walk reports about it."""

    def test_a_folder_asked_for_is_read(self, scan: FolderScan, service: ScanServiceStandIn) -> None:
        scan.start(MANY, lambda _root, _found: None)

        assert [request.root for request in service.started] == [MANY]
        assert scan.phase is ScanPhase.READING

    def test_the_reader_is_told_the_folder_and_the_count(
        self,
        scan: FolderScan,
        service: ScanServiceStandIn,
        heard: Heard,
    ) -> None:
        scan.start(MANY, lambda _root, _found: None)

        service.report(FolderScanStarted(request=service.latest))
        service.report(FolderScanProgress(request=service.latest, count=COUNT))

        assert heard.started == [MANY]
        assert heard.counts == [COUNT]

    def test_what_was_found_reaches_whoever_asked(
        self,
        scan: FolderScan,
        service: ScanServiceStandIn,
        answered: Answered,
    ) -> None:
        scan.start(FEW, answer_into(answered))

        service.report(FolderScanSuccess(request=service.latest, recordings=FOUND))

        assert answered == [(FEW, FOUND)]
        assert scan.phase is ScanPhase.IDLE

    def test_each_reading_answers_the_caller_that_asked_for_it(
        self,
        scan: FolderScan,
        service: ScanServiceStandIn,
    ) -> None:
        """A gathering and a conversion ask the one scan, so a reading answering the other would convert a
        folder nobody asked about."""
        gathered: Answered = []
        converted: Answered = []
        scan.start(MANY, answer_into(gathered))
        service.report(FolderScanSuccess(request=service.latest, recordings=()))

        scan.start(FEW, answer_into(converted))
        service.report(FolderScanSuccess(request=service.latest, recordings=FOUND))

        assert gathered == [(MANY, ())]
        assert converted == [(FEW, FOUND)]

    def test_a_folder_asked_for_while_one_is_read_is_turned_away(
        self,
        scan: FolderScan,
        service: ScanServiceStandIn,
        answered: Answered,
    ) -> None:
        scan.start(MANY, lambda _root, _found: None)

        scan.start(FEW, answer_into(answered))
        service.report(FolderScanSuccess(request=service.latest, recordings=()))

        assert [request.root for request in service.started] == [MANY]
        assert answered == []

    def test_a_failed_reading_is_reported_and_lets_the_next_start(
        self,
        scan: FolderScan,
        service: ScanServiceStandIn,
        heard: Heard,
    ) -> None:
        failure = OSError("the tree went away")
        scan.start(MANY, lambda _root, _found: None)

        service.report(FolderScanError(request=service.latest, exception=failure))
        scan.start(FEW, lambda _root, _found: None)

        assert heard.failures == [failure]
        assert [request.root for request in service.started] == [MANY, FEW]


class TestStoppingAReading:
    """Stop gives a reading up for the reader at once, while the walk winds down until it is heard to give up.

    A folder asked for in that span is read once the walk has given up, the latest one asked for
    taking the place of an earlier one. Reports of the reading let go are set aside.
    """

    @pytest.fixture(name="stopped")
    def stopped_fixture(self, scan: FolderScan, service: ScanServiceStandIn, answered: Answered) -> FolderScan:
        """A reading of the large folder, stopped and winding down."""
        scan.start(MANY, answer_into(answered))
        service.report(FolderScanStarted(request=service.latest))
        scan.stop()
        return scan

    def test_stop_asks_the_walk_to_give_up_once(self, stopped: FolderScan, service: ScanServiceStandIn) -> None:
        stopped.stop()

        assert stopped.phase is ScanPhase.WINDING_DOWN
        assert service.stops == 1

    def test_the_count_of_a_stopped_reading_is_set_aside(
        self,
        stopped: FolderScan,
        service: ScanServiceStandIn,
        heard: Heard,
    ) -> None:
        service.report(FolderScanProgress(request=service.latest, count=COUNT))

        assert heard.counts == []

    def test_the_walk_giving_up_ends_the_reading(
        self,
        stopped: FolderScan,
        service: ScanServiceStandIn,
        heard: Heard,
    ) -> None:
        service.report(FolderScanCanceled(request=service.latest))

        assert heard.stopped == 1
        assert stopped.phase is ScanPhase.IDLE

    def test_a_folder_asked_for_meanwhile_waits_for_the_walk(
        self,
        stopped: FolderScan,
        service: ScanServiceStandIn,
    ) -> None:
        stopped.start(FEW, lambda _root, _found: None)

        assert [request.root for request in service.started] == [MANY]
        assert stopped.phase is ScanPhase.WINDING_DOWN

    def test_the_folder_asked_for_meanwhile_is_read_once_the_walk_gives_up(
        self,
        stopped: FolderScan,
        service: ScanServiceStandIn,
    ) -> None:
        stopped.start(FEW, lambda _root, _found: None)

        service.report(FolderScanCanceled(request=service.latest))

        assert [request.root for request in service.started] == [MANY, FEW]
        assert stopped.phase is ScanPhase.READING

    def test_the_latest_folder_asked_for_is_the_one_read(
        self,
        stopped: FolderScan,
        service: ScanServiceStandIn,
    ) -> None:
        stopped.start(OTHER, lambda _root, _found: None)
        stopped.start(FEW, lambda _root, _found: None)

        service.report(FolderScanCanceled(request=service.latest))

        assert [request.root for request in service.started] == [MANY, FEW]

    def test_the_folder_read_next_answers_its_own_caller(
        self,
        stopped: FolderScan,
        service: ScanServiceStandIn,
        answered: Answered,
    ) -> None:
        converted: Answered = []
        stopped.start(FEW, answer_into(converted))
        service.report(FolderScanCanceled(request=service.latest))

        service.report(FolderScanSuccess(request=service.latest, recordings=FOUND))

        assert answered == []
        assert converted == [(FEW, FOUND)]

    def test_a_walk_finishing_before_it_heard_stop_answers_nobody(
        self,
        stopped: FolderScan,
        service: ScanServiceStandIn,
        heard: Heard,
        answered: Answered,
    ) -> None:
        service.report(FolderScanSuccess(request=service.latest, recordings=FOUND))

        assert answered == []
        assert heard.stopped == 1

    def test_a_walk_failing_as_it_winds_down_ends_the_way_a_stopped_one_does(
        self,
        stopped: FolderScan,
        service: ScanServiceStandIn,
        heard: Heard,
    ) -> None:
        """The reader gave the reading up, so its failure reads as the stop, and the folder asked for meanwhile is read."""
        stopped.start(FEW, lambda _root, _found: None)

        service.report(FolderScanError(request=service.latest, exception=OSError("the tree went away")))

        assert heard.failures == []
        assert heard.stopped == 1
        assert [request.root for request in service.started] == [MANY, FEW]

    def test_a_late_report_of_the_reading_let_go_is_set_aside(
        self,
        stopped: FolderScan,
        service: ScanServiceStandIn,
        heard: Heard,
        answered: Answered,
    ) -> None:
        let_go = service.latest
        stopped.start(FEW, lambda _root, _found: None)
        service.report(FolderScanCanceled(request=let_go))

        service.report(FolderScanProgress(request=let_go, count=COUNT))
        service.report(FolderScanSuccess(request=let_go, recordings=FOUND))

        assert heard.counts == []
        assert answered == []
        assert stopped.phase is ScanPhase.READING

    def test_stop_with_nothing_read_asks_nothing(self, scan: FolderScan, service: ScanServiceStandIn) -> None:
        scan.stop()

        assert service.stops == 0
        assert scan.phase is ScanPhase.IDLE
