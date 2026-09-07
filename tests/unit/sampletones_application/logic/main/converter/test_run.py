from pathlib import Path
from typing import Callable, List, Tuple
from unittest.mock import MagicMock

import pytest

from sampletones_application.logic.main.converter.run import (
    ConversionRun,
    ConversionSuccess,
    RunReport,
)
from sampletones_application.services.conversion.result import ConversionItem, ConversionResult
from sampletones_application.services.result import (
    ServiceCanceled,
    ServiceError,
    ServiceIntermediate,
    ServiceProgress,
    ServiceStarted,
    ServiceSuccess,
)
from sampletones_application.view_model.main.converter import ConversionPhase
from sampletones_core.configs import Config
from sampletones_core.parallelization import TaskProgress
from tests.suite.base import BaseTestSuite
from tests.unit.sampletones_application.logic.main.converter.texts import messages

WRITTEN: Tuple[Path, ...] = (Path("/reconstructions/kick.stn"),)


def _library_progress(completed: int, total: int) -> ConversionResult:
    """The intermediate result the service reports while the library is being generated."""
    return ServiceIntermediate(data=TaskProgress(completed=completed, total=total))


class Driver:
    """A run and the service seam a test reports results through, as the real service would."""

    def __init__(self) -> None:
        self.service = MagicMock()
        self.service.is_running.return_value = False
        self.reports: List[RunReport] = []
        self.run = ConversionRun(self.service, messages=messages())
        self.run.on_report = self.reports.append
        self.run.on_success = MagicMock()
        self.run.on_error = MagicMock()
        self.run.on_canceled = MagicMock()

    @property
    def _handler(self) -> Callable[[ConversionResult], None]:
        handler: Callable[[ConversionResult], None] = self.service.subscribe.call_args.args[0]
        return handler

    def reports_from_service(self, result: ConversionResult) -> None:
        """Hands the run a result the conversion service would report to it."""
        self._handler(result)

    def begin(self, reconstruction_name: str = "kick") -> None:
        self.run.wait()
        self.run.begin(Config(), MagicMock(), reconstruction_name)


@pytest.fixture
def driver() -> Driver:
    return Driver()


class TestWhereARunStands(BaseTestSuite):
    """A run occupies resources from the moment it is requested until it settles."""

    def test_a_fresh_run_is_idle(self, driver: Driver) -> None:
        assert (driver.run.phase, driver.run.is_active) == (ConversionPhase.IDLE, False)

    def test_a_request_waits_for_the_library_it_converts_against(self, driver: Driver) -> None:
        driver.run.wait()

        assert (driver.run.phase, driver.run.is_active) == (ConversionPhase.WAITING, True)

    def test_the_first_progress_puts_the_run_under_way(self, driver: Driver) -> None:
        driver.begin()

        driver.reports_from_service(ServiceProgress(completed=0, total=1))

        assert (driver.run.phase, driver.run.is_active) == (ConversionPhase.RUNNING, True)

    def test_cancelling_holds_resources_until_the_service_answers(self, driver: Driver) -> None:
        driver.begin()

        driver.run.cancel()

        assert (driver.run.phase, driver.run.is_active) == (ConversionPhase.CANCELLING, True)
        driver.service.cancel.assert_called_once()

    @pytest.mark.parametrize(
        ("result", "phase"),
        [
            (ServiceSuccess(value=WRITTEN), ConversionPhase.COMPLETED),
            (ServiceError(exception=RuntimeError("boom")), ConversionPhase.FAILED),
            (ServiceCanceled(), ConversionPhase.CANCELED),
        ],
        ids=["completed", "failed", "canceled"],
    )
    def test_a_settled_run_holds_nothing(
        self,
        driver: Driver,
        result: ConversionResult,
        phase: ConversionPhase,
    ) -> None:
        driver.begin()

        driver.reports_from_service(result)

        assert (driver.run.phase, driver.run.is_active) == (phase, False)


class TestWhatARunReports(BaseTestSuite):
    def test_a_request_says_it_is_waiting(self, driver: Driver) -> None:
        driver.run.wait()

        assert driver.reports[-1].status_text == "main.converter.message.status_waiting"

    def test_progress_names_the_document_being_written(self, driver: Driver) -> None:
        driver.begin(reconstruction_name="track")

        driver.reports_from_service(ServiceProgress(completed=0, total=1))

        assert driver.reports[-1].status_text == "Reconstructing track..."

    def test_progress_names_the_recording_under_way(self, driver: Driver) -> None:
        driver.begin()

        driver.reports_from_service(
            ServiceProgress(completed=0, total=2, current_item=ConversionItem(source=Path("/audio/snare.wav")))
        )

        assert driver.reports[-1].input_path == Path("/audio/snare.wav")

    def test_a_run_naming_no_recording_leaves_the_reader_looking_at_their_own(self, driver: Driver) -> None:
        driver.begin()

        driver.reports_from_service(ServiceProgress(completed=0, total=1))

        assert driver.reports[-1].input_path is None

    def test_a_cancelled_run_keeps_reporting_the_cancelling_line(self, driver: Driver) -> None:
        driver.begin()
        driver.run.cancel()

        driver.reports_from_service(ServiceProgress(completed=1, total=2))

        assert driver.reports[-1].status_text == "main.converter.message.status_cancelling"
        assert driver.run.phase == ConversionPhase.CANCELLING

    def test_library_progress_moves_the_bar_while_waiting(self, driver: Driver) -> None:
        driver.run.wait()

        driver.reports_from_service(ServiceStarted(total=1))
        driver.reports_from_service(_library_progress(completed=3, total=4))

        assert driver.reports[-1].progress == pytest.approx(0.75)

    def test_library_progress_once_the_run_is_under_way_reports_nothing(self, driver: Driver) -> None:
        driver.begin()
        driver.reports_from_service(ServiceProgress(completed=0, total=1))
        reported = len(driver.reports)

        driver.reports_from_service(_library_progress(completed=3, total=4))

        assert len(driver.reports) == reported


class TestWhatACompletedRunHandsOver(BaseTestSuite):
    """A completed conversion tells its listener what it wrote, so the follow-up offer can target
    the single reconstruction or the folder holding a batch."""

    def test_success_carries_the_reconstructions_that_were_written(self, driver: Driver) -> None:
        driver.begin()

        driver.reports_from_service(ServiceSuccess(value=WRITTEN))

        driver.run.on_success.assert_called_once_with(ConversionSuccess(written=WRITTEN))
        assert driver.run.written == WRITTEN

    def test_a_failure_hands_over_the_exception(self, driver: Driver) -> None:
        error = RuntimeError("boom")
        driver.begin()

        driver.reports_from_service(ServiceError(exception=error))

        driver.run.on_error.assert_called_once_with(error)

    def test_a_cancellation_says_so(self, driver: Driver) -> None:
        driver.begin()

        driver.reports_from_service(ServiceCanceled())

        driver.run.on_canceled.assert_called_once_with()

    def test_a_request_given_up_before_the_service_took_it_cancels_all_the_same(self, driver: Driver) -> None:
        driver.run.wait()

        driver.run.abandon()

        driver.run.on_canceled.assert_called_once_with()
        assert driver.run.phase == ConversionPhase.CANCELED

    def test_closing_lets_the_written_reconstructions_go(self, driver: Driver) -> None:
        driver.begin()
        driver.reports_from_service(ServiceSuccess(value=WRITTEN))

        driver.run.close()

        assert (driver.run.written, driver.run.phase) == ((), ConversionPhase.IDLE)
        driver.service.cleanup.assert_called_once()
