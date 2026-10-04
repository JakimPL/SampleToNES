from pathlib import Path
from typing import Iterator, List

import pytest

from sampletones_application.services.folder_scan import service as service_module
from sampletones_application.services.folder_scan.result import (
    FolderScanCanceled,
    FolderScanError,
    FolderScanProgress,
    FolderScanRequest,
    FolderScanResult,
    FolderScanStarted,
    FolderScanSuccess,
)
from sampletones_application.services.folder_scan.service import REPORT_EVERY, FolderScanService
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from tests.suite.files import (
    LOCKED_FOLDER,
    NAMES_ONLY_FOLDER,
    held_at,
    requires_folder_permissions,
)

PRIORITY = 0


@pytest.fixture(name="service")
def service_fixture() -> FolderScanService:
    return FolderScanService(priority=PRIORITY)


@pytest.fixture(name="reports")
def reports_fixture(service: FolderScanService) -> List[FolderScanResult]:
    """Every report the service makes, in the order it makes them."""
    reports: List[FolderScanResult] = []
    service.subscribe(reports.append)
    return reports


@pytest.fixture(name="shutdown")
def shutdown_fixture() -> Iterator[None]:
    """Leaves the executor live for the next case after one that shuts it down."""
    yield
    SingleThreadExecutor.reset_shutdown()


def tree(root: Path, count: int, *, deep: int = 0) -> Path:
    """A folder holding ``count`` recordings, and ``deep`` more in a folder below it."""
    root.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        (root / f"take_{index:04d}.wav").touch()

    if deep:
        tree(root / "below", deep)

    return root


def found(reports: List[FolderScanResult]) -> List[FolderScanSuccess]:
    return [report for report in reports if isinstance(report, FolderScanSuccess)]


class TestWhatAWalkFinds:
    """The walk goes as deep as the folder does and reports what it found against the request."""

    def test_every_recording_below_the_folder(
        self,
        service: FolderScanService,
        reports: List[FolderScanResult],
        tmp_path: Path,
    ) -> None:
        service.start(FolderScanRequest(root=tree(tmp_path / "takes", 3, deep=2)))

        assert len(found(reports)[0].recordings) == 5

    def test_every_report_names_the_request_it_answers(
        self,
        service: FolderScanService,
        reports: List[FolderScanResult],
        tmp_path: Path,
    ) -> None:
        request = FolderScanRequest(root=tree(tmp_path / "takes", REPORT_EVERY))

        service.start(request)

        assert all(report.request is request for report in reports)

    def test_they_arrive_in_name_order(
        self,
        service: FolderScanService,
        reports: List[FolderScanResult],
        tmp_path: Path,
    ) -> None:
        service.start(FolderScanRequest(root=tree(tmp_path / "takes", 4)))

        recordings = found(reports)[0].recordings
        assert list(recordings) == sorted(recordings)

    def test_a_folder_holding_none_answers_with_none(
        self,
        service: FolderScanService,
        reports: List[FolderScanResult],
        tmp_path: Path,
    ) -> None:
        service.start(FolderScanRequest(root=tree(tmp_path / "takes", 0)))

        assert found(reports)[0].recordings == ()

    @requires_folder_permissions
    def test_the_folders_it_may_not_read_are_passed_over(
        self,
        service: FolderScanService,
        reports: List[FolderScanResult],
        tmp_path: Path,
    ) -> None:
        """A locked folder and one listing names only keep their recordings; the rest are found."""
        root = tree(tmp_path / "takes", 2, deep=1)
        locked = tree(root / "locked", 3)
        names_only = tree(root / "names_only", 3)

        with held_at(locked, LOCKED_FOLDER), held_at(names_only, NAMES_ONLY_FOLDER):
            service.start(FolderScanRequest(root=root))

        assert len(found(reports)[0].recordings) == 3


class TestWhatTheReaderIsTold:
    """The reader hears that the reading began and how far it has got."""

    def test_the_reading_says_it_began_before_it_counts(
        self,
        service: FolderScanService,
        reports: List[FolderScanResult],
        tmp_path: Path,
    ) -> None:
        service.start(FolderScanRequest(root=tree(tmp_path / "takes", 1)))

        assert isinstance(reports[0], FolderScanStarted)

    def test_the_count_rises_while_it_walks(
        self,
        service: FolderScanService,
        reports: List[FolderScanResult],
        tmp_path: Path,
    ) -> None:
        service.start(FolderScanRequest(root=tree(tmp_path / "takes", REPORT_EVERY * 2)))

        counts = [report.count for report in reports if isinstance(report, FolderScanProgress)]
        assert counts == [REPORT_EVERY, REPORT_EVERY * 2]


class TestGivingUp:
    """A reader who asked for the wrong folder stops the walk rather than waiting it out."""

    def test_a_stopped_walk_reports_that_it_gave_up(
        self,
        service: FolderScanService,
        reports: List[FolderScanResult],
        tmp_path: Path,
    ) -> None:
        request = FolderScanRequest(root=tree(tmp_path / "takes", REPORT_EVERY * 4))
        service.subscribe(lambda report: service.stop() if isinstance(report, FolderScanProgress) else None)

        service.start(request)

        assert found(reports) == []
        assert reports[-1] == FolderScanCanceled(request=request)

    def test_a_stop_of_one_reading_leaves_the_next_alone(
        self,
        service: FolderScanService,
        reports: List[FolderScanResult],
        tmp_path: Path,
    ) -> None:
        root = tree(tmp_path / "takes", 2)
        service.stop()

        service.start(FolderScanRequest(root=root))

        assert len(found(reports)) == 1

    def test_a_walk_that_fails_reports_its_failure(
        self,
        service: FolderScanService,
        reports: List[FolderScanResult],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        failure = OSError("the tree went away")

        def raising(_root: Path) -> Iterator[Path]:
            raise failure

        monkeypatch.setattr(service_module, "walk_entries", raising)
        service.start(FolderScanRequest(root=tree(tmp_path / "takes", 2)))

        assert isinstance(reports[-1], FolderScanError)
        assert reports[-1].exception is failure

    @requires_folder_permissions
    def test_a_folder_it_may_not_open_reports_its_failure(
        self,
        service: FolderScanService,
        reports: List[FolderScanResult],
        tmp_path: Path,
    ) -> None:
        root = tree(tmp_path / "takes", 2)

        with held_at(root, LOCKED_FOLDER):
            service.start(FolderScanRequest(root=root))

        assert isinstance(reports[-1], FolderScanError)
        assert isinstance(reports[-1].exception, PermissionError)


class TestShuttingDown:
    """A walk ends with the run: a shutdown is heard at the next entry, and nothing reports after it."""

    def test_a_shutdown_ends_the_walk_with_no_report(
        self,
        service: FolderScanService,
        reports: List[FolderScanResult],
        tmp_path: Path,
        shutdown: None,
    ) -> None:
        service.subscribe(
            lambda report: SingleThreadExecutor.request_shutdown() if isinstance(report, FolderScanProgress) else None
        )

        service.start(FolderScanRequest(root=tree(tmp_path / "takes", REPORT_EVERY * 4)))

        assert [type(report) for report in reports] == [FolderScanStarted, FolderScanProgress]

    def test_a_walk_asked_for_after_the_shutdown_never_starts(
        self,
        service: FolderScanService,
        reports: List[FolderScanResult],
        tmp_path: Path,
        shutdown: None,
    ) -> None:
        SingleThreadExecutor.request_shutdown()

        service.start(FolderScanRequest(root=tree(tmp_path / "takes", 2)))

        assert reports == []
