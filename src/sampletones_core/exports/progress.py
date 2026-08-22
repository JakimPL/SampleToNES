from dataclasses import dataclass
from typing import Callable, Final, Optional

from sampletones_core.exports.stage import ExportStage
from sampletones_shared.exceptions import OperationCancelled


@dataclass(frozen=True)
class ExportProgress:
    """How far one stage of an export run has come.

    Attributes:
        stage: The work the run is in the middle of, which names the unit the counts are in.
        completed: What the stage has reached so far.
        total: What the stage counts up to, and ``None`` where the stage runs to a length only
            the data it reads decides.
    """

    stage: ExportStage
    completed: int
    total: Optional[int]


ExportReporter = Callable[[ExportProgress], bool]


def _carry_on(progress: ExportProgress) -> bool:  # pylint: disable=unused-argument
    """Answers that the run goes on, which is what a caller watching nothing asks of a stage."""
    return True


SILENT_REPORTER: Final[ExportReporter] = _carry_on


def announce(
    report: ExportReporter,
    stage: ExportStage,
    completed: int,
    total: Optional[int],
) -> None:
    """Tells a reporter how far a stage has come, and unwinds the run it withdraws.

    Args:
        report: Hears the stage and answers whether the run goes on.
        stage: The work the run is in the middle of.
        completed: What the stage has reached so far.
        total: What the stage counts up to, and ``None`` where only the data decides.

    Raises:
        OperationCancelled: If the run is no longer wanted.
    """
    if not report(ExportProgress(stage=stage, completed=completed, total=total)):
        raise OperationCancelled(f"the export was withdrawn while {stage}")
