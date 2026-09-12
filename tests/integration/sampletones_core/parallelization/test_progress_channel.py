from contextlib import contextmanager
from pathlib import Path
from typing import Final, Iterator, Tuple

import pytest

from sampletones_core.parallelization.task import TaskStatus
from tests.suite.parallelization import (
    COUNTING_STAGE,
    STEP_COUNT,
    CountingProcessor,
    ProgressRecorder,
    several_tasks_reporting,
    stands_partway,
)

READING_TIMEOUT: Final[float] = 60.0
POOL_TIMEOUT: Final[float] = 120.0
ONE_TASK: Final[int] = 1
SEVERAL_TASKS: Final[int] = 3
LONE_WORKER: Final[int] = 1
TWO_WORKERS: Final[int] = 2
FIRST_COUNT: Final[int] = 1
WHOLE_RUN: Final[float] = 1.0
RELEASE_NAME: Final[str] = "release"


@pytest.fixture
def release_path(tmp_path: Path) -> Path:
    """Where a test puts the file its tasks wait on before they finish counting."""
    return tmp_path / RELEASE_NAME


@contextmanager
def counting_run(
    task_count: int,
    release_path: Path,
    workers: int,
) -> Iterator[Tuple[CountingProcessor, ProgressRecorder]]:
    """Starts a counting run, hands the test its recorder, and reaps the pool afterward.

    The release file is written on the way out whatever the test did, so a run whose assertion
    failed before releasing its tasks still ends rather than holding a worker at its halfway mark.
    """
    recorder = ProgressRecorder()
    processor = CountingProcessor(task_count, release_path, max_workers=workers)
    processor.set_callbacks(on_progress=recorder)
    processor.start()
    try:
        yield processor, recorder
    finally:
        release_path.touch(exist_ok=True)
        processor.shutdown()


class TestOneTaskReportsItselfBeforeItFinishes:
    """A run made of a single task says how far that task has come while it is still running.

    Every conversion is one job whatever the number of stems, so a run reporting completions alone
    stands at nothing for its whole length and then jumps to full. The task here is held at its
    halfway mark until the reading below has already been taken, so what each assertion rests on is
    a report that crossed from a live worker process rather than from a finished one.
    """

    def test_a_reading_arrives_from_a_task_still_running(self, release_path: Path) -> None:
        with counting_run(ONE_TASK, release_path, LONE_WORKER) as (processor, recorder):
            assert recorder.wait_for(stands_partway, READING_TIMEOUT)

            release_path.touch()
            processor.wait(POOL_TIMEOUT)

    def test_the_steps_carry_what_the_task_said_of_itself(self, release_path: Path) -> None:
        with counting_run(ONE_TASK, release_path, LONE_WORKER) as (processor, recorder):
            assert recorder.wait_for(stands_partway, READING_TIMEOUT)
            release_path.touch()
            processor.wait(POOL_TIMEOUT)

            steps = recorder.steps
            assert steps
            assert {step.stage for step in steps} == {COUNTING_STAGE}
            assert {step.total for step in steps} == {STEP_COUNT}
            assert all(FIRST_COUNT <= step.completed <= STEP_COUNT for step in steps)
            assert all(step.fraction == step.completed / STEP_COUNT for step in steps)

    def test_the_run_climbs_and_arrives_at_its_end(self, release_path: Path) -> None:
        with counting_run(ONE_TASK, release_path, LONE_WORKER) as (processor, recorder):
            assert recorder.wait_for(stands_partway, READING_TIMEOUT)
            release_path.touch()
            processor.wait(POOL_TIMEOUT)

            fractions = recorder.fractions
            assert fractions == sorted(fractions)
            assert fractions[-1] == WHOLE_RUN
            assert recorder.last_of(TaskStatus.COMPLETED) is not None


class TestSeveralTasksReportSideBySide:
    """Tasks running at once each report on a line of its own, and the run reads them together.

    A finished task's share is let go of as the run counts it, and a report that was already on its
    way is history by then, so the two ways of describing the same work never add up twice — which
    is what keeps the reading inside the run it describes.
    """

    def test_two_tasks_stand_on_their_own_lines_at_once(self, release_path: Path) -> None:
        with counting_run(SEVERAL_TASKS, release_path, TWO_WORKERS) as (processor, recorder):
            assert recorder.wait_for(several_tasks_reporting, READING_TIMEOUT)

            release_path.touch()
            processor.wait(POOL_TIMEOUT)

    def test_the_reading_climbs_and_stays_within_the_run(self, release_path: Path) -> None:
        with counting_run(SEVERAL_TASKS, release_path, TWO_WORKERS) as (processor, recorder):
            assert recorder.wait_for(several_tasks_reporting, READING_TIMEOUT)
            release_path.touch()
            processor.wait(POOL_TIMEOUT)

            fractions = recorder.fractions
            assert fractions == sorted(fractions)
            assert max(fractions) == WHOLE_RUN


class TestAWithdrawalReachesTheTasks:
    """A run let go of unwinds the tasks it handed out, over the same channel they report on.

    The tasks are held at their halfway mark, so the withdrawal below is delivered to workers that
    are provably still running: what ends the run is the answer the reporter gave them, and the
    pool being torn down afterward is the backstop rather than the mechanism.
    """

    def test_a_withdrawn_run_ends_canceled(self, release_path: Path) -> None:
        with counting_run(SEVERAL_TASKS, release_path, TWO_WORKERS) as (processor, recorder):
            assert recorder.wait_for(stands_partway, READING_TIMEOUT)

            processor.cancel()
            release_path.touch()
            processor.wait(POOL_TIMEOUT)

            assert recorder.last_of(TaskStatus.CANCELING) is not None
            assert not processor.is_running()
