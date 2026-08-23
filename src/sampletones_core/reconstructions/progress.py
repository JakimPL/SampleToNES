from dataclasses import dataclass
from typing import Callable, Final

from sampletones_core.reconstructions.stage import ReconstructionStage
from sampletones_shared.exceptions import OperationCancelled
from sampletones_shared.utils.arrays import clamp

STAGE_BEGUN: Final[int] = 0
WHOLE_STAGE: Final[int] = 1

NOTHING_DONE: Final[float] = 0.0
WHOLE_RUN: Final[float] = 1.0


@dataclass(frozen=True)
class ReconstructionProgress:
    """How far one stage of a reconstruction has come.

    Attributes:
        stage: The work the run is in the middle of, which names the unit the counts are in.
        completed: What the stage has reached so far.
        total: What the stage counts up to; a stage announcing its arrival alone counts to one.
    """

    stage: ReconstructionStage
    completed: int
    total: int

    @property
    def fraction(self) -> float:
        """How much of the whole reconstruction stands finished, the stage weighed by its share.

        The stages a run passes through count in units of their own, so a reading that spans them
        all is each stage's own progress taken through the share it holds of the run. The reading
        stays within the run it describes, so whoever draws it is handed a fraction of one.
        """
        if self.total <= 0:
            return self.stage.offset

        reached = self.stage.offset + self.stage.share * (self.completed / self.total)
        return clamp(reached, NOTHING_DONE, WHOLE_RUN)


ReconstructionReporter = Callable[[ReconstructionProgress], bool]


def announce(
    report: ReconstructionReporter,
    stage: ReconstructionStage,
    completed: int,
    total: int,
) -> None:
    """Tells a reporter how far a stage has come, and unwinds the run it withdraws.

    Args:
        report: Hears the stage and answers whether the run goes on.
        stage: The work the run is in the middle of.
        completed: What the stage has reached so far.
        total: What the stage counts up to.

    Raises:
        OperationCancelled: If the run is no longer wanted.
    """
    if not report(ReconstructionProgress(stage=stage, completed=completed, total=total)):
        raise OperationCancelled(f"the reconstruction was withdrawn while {stage}")
