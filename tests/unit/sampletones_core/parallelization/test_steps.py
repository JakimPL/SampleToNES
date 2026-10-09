from dataclasses import dataclass
from typing import Final, Tuple

import pytest

from sampletones_core.parallelization.steps import TaskSteps
from sampletones_core.parallelization.task import TaskProgress, TaskReport, TaskStep
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

STAGE: Final[str] = "matching"
TOTAL: Final[int] = 4
FIRST: Final[int] = 0
SECOND: Final[int] = 1
THIRD: Final[int] = 2


def _report(index: int, completed: int) -> TaskReport:
    return TaskReport(
        index=index,
        step=TaskStep(stage=STAGE, completed=completed, total=TOTAL, fraction=completed / TOTAL),
    )


class TestWhereTheRunningTasksStand(BaseTestSuite):
    """The table holds one step per running task, in the order the run handed the tasks out."""

    def test_a_task_reporting_twice_stands_where_it_last_said(self) -> None:
        steps = TaskSteps()

        steps.record(_report(FIRST, 1))
        steps.record(_report(FIRST, 3))

        assert steps.snapshot() == (_report(FIRST, 3).step,)

    def test_the_snapshot_follows_the_order_the_tasks_were_handed_out(self) -> None:
        steps = TaskSteps()

        steps.record(_report(THIRD, 1))
        steps.record(_report(FIRST, 2))
        steps.record(_report(SECOND, 3))

        assert steps.snapshot() == (
            _report(FIRST, 2).step,
            _report(SECOND, 3).step,
            _report(THIRD, 1).step,
        )

    def test_a_finished_task_is_let_go_of(self) -> None:
        steps = TaskSteps()
        steps.record(_report(FIRST, 2))
        steps.record(_report(SECOND, 1))

        steps.complete(FIRST)

        assert steps.snapshot() == (_report(SECOND, 1).step,)

    def test_a_report_arriving_after_its_task_finished_is_history(self) -> None:
        steps = TaskSteps()
        steps.record(_report(FIRST, 2))

        steps.complete(FIRST)
        steps.record(_report(FIRST, 4))

        assert steps.snapshot() == ()

    def test_a_task_finishing_before_it_ever_reported_costs_nothing(self) -> None:
        steps = TaskSteps()

        steps.complete(SECOND)

        assert steps.snapshot() == ()

    def test_a_cleared_table_takes_a_new_run_as_it_comes(self) -> None:
        steps = TaskSteps()
        steps.record(_report(FIRST, 2))
        steps.complete(FIRST)

        steps.clear()
        steps.record(_report(FIRST, 1))

        assert steps.snapshot() == (_report(FIRST, 1).step,)


class TestHowFullARunStands(BaseTestSuite):
    """A run reads as the tasks it finished plus the part of each running task that is done."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: float
        total: int
        completed: int
        fractions: Tuple[float, ...]

    test_cases = (
        TestCase(label="a_run_with_nothing_to_do", total=0, completed=0, fractions=(), expected=0.0),
        TestCase(label="one_task_untouched", total=1, completed=0, fractions=(), expected=0.0),
        TestCase(label="one_task_partway", total=1, completed=0, fractions=(0.25,), expected=0.25),
        TestCase(label="one_task_done", total=1, completed=1, fractions=(), expected=1.0),
        TestCase(label="two_of_four_and_one_partway", total=4, completed=2, fractions=(0.5,), expected=0.625),
        TestCase(label="two_tasks_partway", total=4, completed=1, fractions=(0.5, 0.25), expected=0.4375),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_fraction_counts_the_work_under_way(self, test_case: TestCase) -> None:
        progress = TaskProgress(
            total=test_case.total,
            completed=test_case.completed,
            steps=tuple(
                TaskStep(stage=STAGE, completed=1, total=TOTAL, fraction=fraction) for fraction in test_case.fractions
            ),
        )

        assert progress.fraction == pytest.approx(test_case.expected)

    def test_a_run_reporting_no_steps_reads_as_its_completed_tasks(self) -> None:
        progress = TaskProgress(total=4, completed=3)

        assert progress.partial == 0.0
        assert progress.fraction == pytest.approx(0.75)
