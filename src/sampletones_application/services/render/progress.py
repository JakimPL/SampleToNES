from typing import Callable

from sampletones_application.services.render.constants import PROGRESS_STEPS
from sampletones_application.services.render.result import RenderStage
from sampletones_application.services.result import ServiceProgress
from sampletones_core.parallelization import ETAEstimator


class StageProgress:
    """One pass of a render, reported at a bounded rate.

    A render walks a song sample by sample, so reporting every step would fill the callback
    queue with updates no eye resolves and no bar redraws. Emitting on a fraction of the total
    holds the report rate steady whatever the song's length, and the last position is always
    reported, so a bar arrives at its end.
    """

    def __init__(
        self,
        stage: RenderStage,
        total: int,
        *,
        emit: Callable[[ServiceProgress[RenderStage]], None],
    ) -> None:
        self._stage = stage
        self._total = total
        self._emit = emit
        self._estimator = ETAEstimator(total=total)
        self._interval = max(1, total // PROGRESS_STEPS)
        self._reported: int = 0

    def advance(self, completed: int) -> None:
        """Reports the pass at ``completed`` samples where a step is due.

        Args:
            completed: The samples this pass has covered so far.
        """
        if completed < self._total and completed - self._reported < self._interval:
            return

        self._reported = completed
        self._emit(
            ServiceProgress(
                completed=completed,
                total=self._total,
                current_item=self._stage,
                eta_seconds=self._estimator.update(completed),
            )
        )
