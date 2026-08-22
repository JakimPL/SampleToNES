from typing import Final, Generic, List, Optional, Sequence, TypeVar

from sampletones_core.exports.progress import ExportProgress
from sampletones_core.exports.stage import ExportStage

ProgressT = TypeVar("ProgressT")

NEVER_WITHDRAWN: Final[Optional[int]] = None
FIRST_REPORT: Final[int] = 1


class RecordingReporter(Generic[ProgressT]):
    """Keeps every report a run offers, and withdraws the run at a chosen one.

    A run reports itself so a caller can watch it and decide whether it goes on, so a test of
    one asks two things: what the run said about itself, and what it did once told to stop.
    Both are answered here, the second by counting the reports and refusing at the one named.
    """

    def __init__(self, withdraw_at: Optional[int] = NEVER_WITHDRAWN) -> None:
        self.reports: List[ProgressT] = []
        self._withdraw_at = withdraw_at

    def __call__(self, progress: ProgressT) -> bool:
        self.reports.append(progress)
        return len(self.reports) != self._withdraw_at

    @property
    def last(self) -> ProgressT:
        """The report the run finished on."""
        return self.reports[-1]


def reported_stages(reports: Sequence[ExportProgress]) -> List[ExportStage]:
    """The stages a run reached, in order, a stretch spent in one counted once.

    Args:
        reports: What the run said about itself, in the order it said it.

    Returns:
        List[ExportStage]: The stages, each entry a stage the run moved into.
    """
    reached: List[ExportStage] = []
    for report in reports:
        if not reached or reached[-1] != report.stage:
            reached.append(report.stage)

    return reached
