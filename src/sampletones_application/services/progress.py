from typing import Callable, Final, Generic, Optional, TypeVar

from sampletones_application.services.result import ServiceProgress
from sampletones_core.parallelization import ETAEstimator

StageT = TypeVar("StageT")

PROGRESS_STEPS: Final[int] = 200
UNMEASURED: Final[int] = 0


class StageProgress(Generic[StageT]):
    """One stage of a long operation, reported at a bounded rate.

    A stage may step through millions of samples or a few files, so reporting every step would
    fill the callback queue with updates no eye resolves and no bar redraws. Emitting on a
    fraction of what the stage is measured against holds the report rate steady whatever the work
    is, and a stage landing on its total is always reported, so a bar arrives at its end.

    What a stage counts moves by its own rules: a render's samples rise toward the song's length,
    while a compression's bytes fall as the dictionary earns its keep. A step is therefore a
    change of either sign.
    """

    def __init__(
        self,
        stage: StageT,
        total: int,
        *,
        emit: Callable[[ServiceProgress[StageT]], None],
        estimates: bool,
    ) -> None:
        """Holds one stage's reporting.

        Args:
            stage: The work being reported, which names the unit the counts are in.
            total: What the stage's count is measured against, and ``UNMEASURED`` where nothing
                bounds it.
            emit: Carries a report to the service's subscribers.
            estimates: Whether the count reaches ``total`` at a rate a remaining time can be read
                from. A stage measured against a limit it is not travelling toward states no
                estimate, since one taken from that would be a guess wearing the clothes of a fact.
        """
        self._stage = stage
        self._total = total
        self._emit = emit
        self._estimator = ETAEstimator(total=total) if estimates and total > UNMEASURED else None
        self._interval = max(1, total // PROGRESS_STEPS)
        self._reported: int = 0

    def advance(self, completed: int) -> None:
        """Reports the stage at ``completed`` where a step is due.

        Args:
            completed: What the stage has covered so far, in the unit the stage counts in.
        """
        if completed != self._total and abs(completed - self._reported) < self._interval:
            return

        self._reported = completed
        self._emit(
            ServiceProgress(
                completed=completed,
                total=self._total,
                current_item=self._stage,
                eta_seconds=self._estimate(completed),
            )
        )

    def _estimate(self, completed: int) -> Optional[float]:
        if self._estimator is None:
            return None

        return self._estimator.update(completed)
