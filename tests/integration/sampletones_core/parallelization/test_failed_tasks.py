from typing import Final, List, Tuple

import pytest
from pebble import ProcessExpired

from sampletones_core.parallelization.outcome import RunCompleted
from tests.suite.base import BaseTestSuite
from tests.suite.parallelization import FatedProcessor, TaskFate

TWO_WORKERS: Final[int] = 2
FATES: Final[Tuple[TaskFate, ...]] = (
    TaskFate.ANSWERS,
    TaskFate.RAISES,
    TaskFate.ANSWERS,
    TaskFate.DIES,
    TaskFate.ANSWERS,
)


class TestARunGoingOnPastFailingTasks(BaseTestSuite):
    """A run that skips failing tasks answers every other task and names each one that failed, whether the
    task raised or its worker died. A run that does not skip them ends with the first error."""

    def test_the_answers_and_the_failures_are_both_named(self) -> None:
        completed: List[RunCompleted[int]] = []
        run = FatedProcessor(FATES, skips=True, max_workers=TWO_WORKERS)
        run.set_callbacks(on_completed=completed.append)

        run.start()
        run.wait()

        (outcome,) = completed
        assert outcome.results == [0, 2, 4]
        assert [failure.index for failure in outcome.failures] == [1, 3]
        assert isinstance(outcome.failures[0].exception, ValueError)
        assert isinstance(outcome.failures[1].exception, ProcessExpired)

    def test_a_run_holding_to_its_tasks_ends_with_the_first_error(self) -> None:
        completed: List[RunCompleted[int]] = []
        errors: List[Exception] = []
        run = FatedProcessor(FATES, skips=False, max_workers=TWO_WORKERS)
        run.set_callbacks(on_completed=completed.append, on_error=errors.append)

        run.start()
        with pytest.raises(ValueError):
            run.wait()

        assert completed == []
        assert [type(error) for error in errors] == [ValueError]
