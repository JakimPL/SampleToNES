from typing import Final, List

from sampletones_application.services.progress import (
    PROGRESS_STEPS,
    UNMEASURED,
    StageProgress,
)
from sampletones_application.services.render.result import RenderStage
from sampletones_application.services.result import ServiceProgress
from sampletones_core.exports.stage import ExportStage

TOTAL_SAMPLES: Final[int] = PROGRESS_STEPS * 100
STEP: Final[int] = TOTAL_SAMPLES // PROGRESS_STEPS
PROGRAM_AREA: Final[int] = 32429
FIRST_SIZE: Final[int] = 12689
SMALLER_SIZE: Final[int] = FIRST_SIZE - PROGRAM_AREA // PROGRESS_STEPS - 1


class TestReportingAtABoundedRate:
    """A stage reports on a fraction of what it is measured against, whatever its length."""

    def test_a_step_reaches_the_subscriber(self) -> None:
        reports: List[ServiceProgress[RenderStage]] = []
        progress = StageProgress(RenderStage.SYNTHESIS, TOTAL_SAMPLES, emit=reports.append, estimates=True)
        progress.advance(STEP)
        assert reports[-1].completed == STEP

    def test_a_move_short_of_a_step_is_held_back(self) -> None:
        reports: List[ServiceProgress[RenderStage]] = []
        progress = StageProgress(RenderStage.SYNTHESIS, TOTAL_SAMPLES, emit=reports.append, estimates=True)
        progress.advance(STEP - 1)
        assert reports == []

    def test_a_stage_landing_on_its_total_is_always_reported(self) -> None:
        reports: List[ServiceProgress[RenderStage]] = []
        progress = StageProgress(RenderStage.SYNTHESIS, TOTAL_SAMPLES, emit=reports.append, estimates=True)
        progress.advance(TOTAL_SAMPLES)
        progress.advance(TOTAL_SAMPLES)
        assert [report.completed for report in reports] == [TOTAL_SAMPLES, TOTAL_SAMPLES]

    def test_the_stage_names_what_the_counts_are_in(self) -> None:
        reports: List[ServiceProgress[RenderStage]] = []
        progress = StageProgress(RenderStage.ENCODING, TOTAL_SAMPLES, emit=reports.append, estimates=True)
        progress.advance(TOTAL_SAMPLES)
        assert reports[-1].current_item == RenderStage.ENCODING


class TestACountThatFalls:
    """A compression's bytes fall as the dictionary earns its keep, and that is still a step."""

    def test_a_fall_of_a_step_is_reported(self) -> None:
        reports: List[ServiceProgress[ExportStage]] = []
        progress = StageProgress(ExportStage.COMPRESSING, PROGRAM_AREA, emit=reports.append, estimates=False)
        progress.advance(FIRST_SIZE)
        progress.advance(SMALLER_SIZE)
        assert [report.completed for report in reports] == [FIRST_SIZE, SMALLER_SIZE]


class TestWhereAnEstimateStands:
    """A remaining time is stated only where the count travels toward the total."""

    def test_a_stage_travelling_to_its_total_estimates(self) -> None:
        reports: List[ServiceProgress[RenderStage]] = []
        progress = StageProgress(RenderStage.SYNTHESIS, TOTAL_SAMPLES, emit=reports.append, estimates=True)
        progress.advance(TOTAL_SAMPLES)
        assert reports[-1].eta_seconds is not None

    def test_a_stage_measured_against_a_limit_states_none(self) -> None:
        reports: List[ServiceProgress[ExportStage]] = []
        progress = StageProgress(ExportStage.COMPRESSING, PROGRAM_AREA, emit=reports.append, estimates=False)
        progress.advance(FIRST_SIZE)
        assert reports[-1].eta_seconds is None

    def test_a_stage_with_nothing_to_measure_against_states_none(self) -> None:
        reports: List[ServiceProgress[ExportStage]] = []
        progress = StageProgress(ExportStage.WALKING, UNMEASURED, emit=reports.append, estimates=True)
        progress.advance(UNMEASURED)
        assert reports[-1].eta_seconds is None
