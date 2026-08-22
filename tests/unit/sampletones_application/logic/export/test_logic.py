from typing import Callable, Final, List, Optional

import pytest

from sampletones_application.logic.export import SongExportLogic
from sampletones_application.services.export.kind import ExportKind
from sampletones_application.services.export.result import ExportResult, ExportSuccess
from sampletones_application.services.result import (
    ServiceCancelled,
    ServiceProgress,
    ServiceStarted,
)
from sampletones_application.view_model.shared.export import (
    ExportPhase,
    SongExportViewModel,
)
from sampletones_core.exports.stage import ExportStage

WALKING_LABEL: Final[str] = "Playing the song out"
COMPRESSING_LABEL: Final[str] = "Compressing the song"
WRITING_LABEL: Final[str] = "Writing the file"
SIZE_TEMPLATE: Final[str] = "{completed} of {total} bytes"
CANCELLING_LABEL: Final[str] = "Stopping the export..."
NOTHING_MEASURED: Final[int] = 0
PROGRAM_AREA: Final[int] = 32429
SONG_TICKS: Final[int] = 14400
REACHED_SIZE: Final[int] = 8761
WALKED_TICKS: Final[int] = 7200


class FakeExportService:
    """The export service as the dialog's logic drives it, holding what it was asked to do."""

    def __init__(self, *, running: bool = True) -> None:
        self.running = running
        self.cancels: int = 0
        self.shutdowns: int = 0
        self._handler: Optional[Callable[[ExportResult], None]] = None

    def subscribe(self, handler: Callable[[ExportResult], None]) -> None:
        self._handler = handler

    def cancel(self) -> None:
        self.cancels += 1

    def is_running(self) -> bool:
        return self.running

    def shutdown(self) -> None:
        self.shutdowns += 1

    def deliver(self, result: ExportResult) -> None:
        assert self._handler is not None
        self._handler(result)


def progress(
    stage: ExportStage,
    completed: int,
    total: int,
) -> ServiceProgress[ExportStage]:
    return ServiceProgress(completed=completed, total=total, current_item=stage)


@pytest.fixture(name="service")
def service_fixture() -> FakeExportService:
    return FakeExportService()


@pytest.fixture(name="logic")
def logic_fixture(service: FakeExportService) -> SongExportLogic:
    return SongExportLogic(
        service,
        stage_labels={
            ExportStage.WALKING: WALKING_LABEL,
            ExportStage.COMPRESSING: COMPRESSING_LABEL,
            ExportStage.WRITING: WRITING_LABEL,
        },
        size_template=SIZE_TEMPLATE,
        cancelling_label=CANCELLING_LABEL,
    )


@pytest.fixture(name="views")
def views_fixture(logic: SongExportLogic) -> List[SongExportViewModel]:
    views: List[SongExportViewModel] = []
    logic.on_view_changed = views.append
    return views


def finished() -> ExportSuccess:
    from pathlib import Path

    return ExportSuccess(
        kind=ExportKind.SAMPLE,
        filepath=Path("song.nsf"),
        export_format=None,
        truncation=None,
    )


class TestFollowingARun:
    """The stages are listed as the format reaches them, so the run's shape is learned."""

    def test_a_start_puts_the_dialog_on_screen(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
    ) -> None:
        opened: List[bool] = []
        logic.on_started = lambda: opened.append(True)
        service.deliver(ServiceStarted(total=NOTHING_MEASURED))
        assert opened == [True]

    def test_a_stage_joins_the_list_when_the_run_reaches_it(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
        views: List[SongExportViewModel],
    ) -> None:
        service.deliver(ServiceStarted(total=NOTHING_MEASURED))
        service.deliver(progress(ExportStage.WALKING, WALKED_TICKS, SONG_TICKS))
        service.deliver(progress(ExportStage.COMPRESSING, REACHED_SIZE, PROGRAM_AREA))
        assert views[-1].stages == (ExportStage.WALKING, ExportStage.COMPRESSING)

    def test_a_stage_reported_again_is_listed_once(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
        views: List[SongExportViewModel],
    ) -> None:
        service.deliver(ServiceStarted(total=NOTHING_MEASURED))
        service.deliver(progress(ExportStage.COMPRESSING, REACHED_SIZE, PROGRAM_AREA))
        service.deliver(progress(ExportStage.COMPRESSING, REACHED_SIZE - 100, PROGRAM_AREA))
        assert views[-1].stages == (ExportStage.COMPRESSING,)

    def test_a_second_run_starts_the_list_over(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
        views: List[SongExportViewModel],
    ) -> None:
        service.deliver(ServiceStarted(total=NOTHING_MEASURED))
        service.deliver(progress(ExportStage.WRITING, 1, 1))
        service.deliver(finished())
        service.deliver(ServiceStarted(total=NOTHING_MEASURED))
        assert views[-1].stages == ()


class TestHowEachStageReads:
    """A stage travelling to an end is a fraction; one measured against a limit is a figure."""

    def test_a_travelling_stage_carries_its_share(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
        views: List[SongExportViewModel],
    ) -> None:
        service.deliver(ServiceStarted(total=NOTHING_MEASURED))
        service.deliver(progress(ExportStage.WALKING, WALKED_TICKS, SONG_TICKS))
        assert views[-1].progress == pytest.approx(WALKED_TICKS / SONG_TICKS)

    def test_a_travelling_stage_states_no_figure(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
        views: List[SongExportViewModel],
    ) -> None:
        service.deliver(ServiceStarted(total=NOTHING_MEASURED))
        service.deliver(progress(ExportStage.WALKING, WALKED_TICKS, SONG_TICKS))
        assert views[-1].figure == ""

    def test_a_stage_measured_against_a_limit_spells_out_what_it_holds(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
        views: List[SongExportViewModel],
    ) -> None:
        service.deliver(ServiceStarted(total=NOTHING_MEASURED))
        service.deliver(progress(ExportStage.COMPRESSING, REACHED_SIZE, PROGRAM_AREA))
        assert views[-1].figure == f"{REACHED_SIZE} of {PROGRAM_AREA} bytes"

    def test_a_stage_measured_against_a_limit_carries_no_bar(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
        views: List[SongExportViewModel],
    ) -> None:
        service.deliver(ServiceStarted(total=NOTHING_MEASURED))
        service.deliver(progress(ExportStage.COMPRESSING, REACHED_SIZE, PROGRAM_AREA))
        assert views[-1].travelling is False

    def test_a_stage_with_nothing_to_measure_against_stands_at_the_start(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
        views: List[SongExportViewModel],
    ) -> None:
        service.deliver(ServiceStarted(total=NOTHING_MEASURED))
        service.deliver(progress(ExportStage.WALKING, NOTHING_MEASURED, NOTHING_MEASURED))
        assert views[-1].progress == 0.0


class TestStoppingARun:
    """A stop reaches the service, and what the dialog says holds until the outcome arrives."""

    def test_a_stop_reaches_the_service(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
    ) -> None:
        service.deliver(ServiceStarted(total=NOTHING_MEASURED))
        logic.cancel()
        assert service.cancels == 1

    def test_a_stop_says_so(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
        views: List[SongExportViewModel],
    ) -> None:
        service.deliver(ServiceStarted(total=NOTHING_MEASURED))
        logic.cancel()
        assert views[-1].figure == CANCELLING_LABEL

    def test_a_report_arriving_after_a_stop_leaves_the_message_standing(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
        views: List[SongExportViewModel],
    ) -> None:
        service.deliver(ServiceStarted(total=NOTHING_MEASURED))
        logic.cancel()
        service.deliver(progress(ExportStage.COMPRESSING, REACHED_SIZE, PROGRAM_AREA))
        assert views[-1].figure == CANCELLING_LABEL

    def test_a_stop_asked_of_nothing_reaches_no_service(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
    ) -> None:
        service.running = False
        logic.cancel()
        assert service.cancels == 0

    def test_exiting_winds_a_running_export_down(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
    ) -> None:
        logic.cleanup()
        assert service.shutdowns == 1


class TestTheOutcomeThatCloses:
    """Whatever the run answered with, the dialog hands the screen back."""

    def test_a_finished_run_takes_the_dialog_off_screen(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
    ) -> None:
        closed: List[bool] = []
        logic.on_finished = lambda: closed.append(True)
        service.deliver(ServiceStarted(total=NOTHING_MEASURED))
        service.deliver(finished())
        assert closed == [True]

    def test_a_cancelled_run_takes_the_dialog_off_screen(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
    ) -> None:
        closed: List[bool] = []
        logic.on_finished = lambda: closed.append(True)
        service.deliver(ServiceStarted(total=NOTHING_MEASURED))
        service.deliver(ServiceCancelled())
        assert closed == [True]

    def test_a_run_that_ended_holds_the_screen_no_longer(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
    ) -> None:
        service.deliver(ServiceStarted(total=NOTHING_MEASURED))
        service.deliver(finished())
        assert logic.is_active is False

    def test_a_running_export_holds_the_screen(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
    ) -> None:
        service.deliver(ServiceStarted(total=NOTHING_MEASURED))
        assert logic.is_active is True

    def test_the_phase_returns_to_idle(
        self,
        logic: SongExportLogic,
        service: FakeExportService,
        views: List[SongExportViewModel],
    ) -> None:
        service.deliver(ServiceStarted(total=NOTHING_MEASURED))
        service.deliver(finished())
        assert views[-1].phase == ExportPhase.IDLE
