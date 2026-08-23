from typing import Final, List

import pytest

from sampletones_core.parallelization.task import TaskStep
from sampletones_core.reconstructions.converter.progress import JobReporter
from sampletones_core.reconstructions.progress import ReconstructionProgress, announce
from sampletones_core.reconstructions.stage import ReconstructionStage
from sampletones_shared.exceptions import OperationCancelled
from sampletones_shared.utils.progress import PROGRESS_STEPS
from tests.suite.base import BaseTestSuite

FRAMES: Final[int] = PROGRESS_STEPS * 10
WHOLE_STAGE: Final[int] = 1
STAGE_BEGUN: Final[int] = 0


class RecordingLine:
    """A line that keeps the steps a job filed, and withdraws the run after a chosen number.

    Stands in for the line a job reports on so a test reads what the job said without a worker
    process on the other end of it.
    """

    def __init__(self, withdraw_after: int = 0) -> None:
        self.steps: List[TaskStep] = []
        self._withdraw_after = withdraw_after

    def __call__(self, step: TaskStep) -> bool:
        self.steps.append(step)
        return not self._withdraw_after or len(self.steps) < self._withdraw_after


class TestWhatAJobFiles(BaseTestSuite):
    """A job's step names the stage it is in and how far the whole job has come."""

    def test_a_step_carries_the_stage_and_its_counts(self) -> None:
        line = RecordingLine()
        reporter = JobReporter(line)

        reporter(ReconstructionProgress(stage=ReconstructionStage.MATCHING, completed=0, total=FRAMES))

        assert line.steps == [
            TaskStep(
                stage=ReconstructionStage.MATCHING.value,
                completed=0,
                total=FRAMES,
                fraction=ReconstructionStage.MATCHING.offset,
            )
        ]

    def test_the_fraction_weighs_the_stage_into_the_whole_job(self) -> None:
        line = RecordingLine()
        reporter = JobReporter(line)

        reporter(ReconstructionProgress(stage=ReconstructionStage.MATCHING, completed=FRAMES, total=FRAMES))

        filed = line.steps[-1]
        assert filed.fraction == pytest.approx(ReconstructionStage.MATCHING.offset + ReconstructionStage.MATCHING.share)

    def test_every_stage_is_heard_from_as_it_begins(self) -> None:
        line = RecordingLine()
        reporter = JobReporter(line)

        for stage in ReconstructionStage:
            reporter(ReconstructionProgress(stage=stage, completed=STAGE_BEGUN, total=WHOLE_STAGE))

        assert [step.stage for step in line.steps] == [stage.value for stage in ReconstructionStage]


class TestHowOftenAJobIsHeardFrom(BaseTestSuite):
    """A frame-by-frame account is carried at a rate a line and a bar can keep up with."""

    def test_a_long_stage_files_about_as_many_steps_as_a_bar_has(self) -> None:
        line = RecordingLine()
        reporter = JobReporter(line)

        for frame in range(FRAMES + 1):
            reporter(ReconstructionProgress(stage=ReconstructionStage.MATCHING, completed=frame, total=FRAMES))

        assert len(line.steps) == pytest.approx(PROGRESS_STEPS + 1, abs=1)

    def test_a_stage_is_heard_from_where_it_lands(self) -> None:
        line = RecordingLine()
        reporter = JobReporter(line)

        for frame in range(FRAMES + 1):
            reporter(ReconstructionProgress(stage=ReconstructionStage.MATCHING, completed=frame, total=FRAMES))

        assert line.steps[-1].completed == FRAMES

    def test_each_stage_is_spaced_by_its_own_length(self) -> None:
        line = RecordingLine()
        reporter = JobReporter(line)

        reporter(ReconstructionProgress(stage=ReconstructionStage.MATCHING, completed=0, total=FRAMES))
        reporter(ReconstructionProgress(stage=ReconstructionStage.DECODING, completed=0, total=WHOLE_STAGE))
        reporter(ReconstructionProgress(stage=ReconstructionStage.DECODING, completed=WHOLE_STAGE, total=WHOLE_STAGE))

        assert [step.stage for step in line.steps] == [
            ReconstructionStage.MATCHING.value,
            ReconstructionStage.DECODING.value,
            ReconstructionStage.DECODING.value,
        ]


class TestAWithdrawalReachingTheJob(BaseTestSuite):
    """A job told the run has been let go of unwinds where it stands."""

    def test_a_withdrawn_job_unwinds_at_its_next_frame(self) -> None:
        line = RecordingLine(withdraw_after=1)
        reporter = JobReporter(line)

        with pytest.raises(OperationCancelled):
            for frame in range(FRAMES + 1):
                announce(reporter, ReconstructionStage.MATCHING, frame, FRAMES)

    def test_a_job_the_run_still_wants_carries_on(self) -> None:
        line = RecordingLine()
        reporter = JobReporter(line)

        for frame in range(FRAMES + 1):
            announce(reporter, ReconstructionStage.MATCHING, frame, FRAMES)

        assert line.steps
