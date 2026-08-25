from typing import Optional

from sampletones_core.parallelization.channel.protocol import StepReporter
from sampletones_core.parallelization.task import TaskStep
from sampletones_core.reconstructions.progress import ReconstructionProgress
from sampletones_core.reconstructions.stage import ReconstructionStage
from sampletones_shared.utils.progress import ReportRate


class JobReporter:
    """Carries one job's account of itself back to the run that handed it out.

    A reconstruction says where it stands frame by frame, far more often than a line can carry or a
    bar can be redrawn, so each stage is reported at the spacing its own length sets. The stage is
    weighed into a reading of the whole job before it travels, since the run counts jobs and knows
    nothing of the frames one is made of.

    The line answers in both directions, so a job that hears the run has been let go of says so
    where it stands and the reconstruction unwinds from that frame.
    """

    def __init__(self, report: StepReporter) -> None:
        """Holds the line one job reports on.

        Args:
            report: Carries a step to the run, and answers whether that run goes on.
        """
        self._report = report
        self._stage: Optional[ReconstructionStage] = None
        self._rate: Optional[ReportRate] = None

    def __call__(self, progress: ReconstructionProgress) -> bool:
        """Files the job's step where one is due, and answers whether the run goes on.

        Args:
            progress: Where the reconstruction now stands.

        Returns:
            bool: Whether the run still wants the reconstruction this job is building.
        """
        if not self._rate_for(progress).take(progress.completed):
            return True

        return self._report(
            TaskStep(
                stage=progress.stage.value,
                completed=progress.completed,
                total=progress.total,
                fraction=progress.fraction,
            )
        )

    def _rate_for(self, progress: ReconstructionProgress) -> ReportRate:
        """The spacing the stage is reported at, which each stage sets by its own length."""
        if self._rate is None or self._stage != progress.stage:
            self._stage = progress.stage
            self._rate = ReportRate(progress.total)

        return self._rate
