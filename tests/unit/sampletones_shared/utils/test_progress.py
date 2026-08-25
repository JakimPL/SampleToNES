from dataclasses import dataclass
from typing import Final, List, Tuple

import pytest

from sampletones_shared.utils.progress import (
    PROGRESS_STEPS,
    ReportRate,
    report_interval,
    silent_reporter,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase

LONG_STAGE: Final[int] = PROGRESS_STEPS * 100
SHORT_STAGE: Final[int] = 3
UNMEASURED_STAGE: Final[int] = 0
ONE_STEP: Final[int] = 1


class TestHowOftenAStageIsWorthReporting(BaseTestSuite):
    """The spacing between reports follows the length of the stage, never the size of its steps."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: int
        total: int

        @property
        def label(self) -> str:
            return f"a_stage_counting_to_{self.total}"

    test_cases = (
        TestCase(total=UNMEASURED_STAGE, expected=ONE_STEP),
        TestCase(total=SHORT_STAGE, expected=ONE_STEP),
        TestCase(total=PROGRESS_STEPS, expected=ONE_STEP),
        TestCase(total=LONG_STAGE, expected=LONG_STAGE // PROGRESS_STEPS),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_stage_is_reported_over_a_fixed_number_of_steps(self, test_case: TestCase) -> None:
        assert report_interval(test_case.total) == test_case.expected

    def test_a_stage_shorter_than_the_steps_reports_every_count(self) -> None:
        rate = ReportRate(SHORT_STAGE)

        assert [rate.take(completed) for completed in range(SHORT_STAGE + 1)] == [True] * (SHORT_STAGE + 1)


class TestTakingAReading(BaseTestSuite):
    """A rate takes the readings that are due and lets the rest of a stage's steps pass."""

    def test_a_long_stage_is_reported_about_as_often_as_it_has_steps(self) -> None:
        rate = ReportRate(LONG_STAGE)

        taken = [completed for completed in range(LONG_STAGE + 1) if rate.take(completed)]

        assert len(taken) == pytest.approx(PROGRESS_STEPS + 1, abs=ONE_STEP)

    def test_a_stage_landing_on_its_total_is_always_reported(self) -> None:
        rate = ReportRate(LONG_STAGE)
        rate.take(0)

        assert rate.take(LONG_STAGE)

    def test_a_count_falling_toward_its_total_is_a_step_the_same_way(self) -> None:
        rate = ReportRate(LONG_STAGE)
        rate.take(LONG_STAGE)

        assert rate.take(LONG_STAGE // 2)

    def test_a_reading_is_measured_from_the_one_before_it(self) -> None:
        rate = ReportRate(LONG_STAGE)
        interval = report_interval(LONG_STAGE)
        rate.take(0)

        assert not rate.take(interval - ONE_STEP)
        assert rate.take(interval)


class TestACallerWatchingNothing(BaseTestSuite):
    """A run reported to nobody still asks whether it goes on, and hears that it does."""

    def test_the_silent_reporter_lets_every_run_through(self) -> None:
        readings: Tuple[object, ...] = ("a stage", 1, None)
        answers: List[bool] = [silent_reporter(reading) for reading in readings]

        assert answers == [True] * len(readings)
