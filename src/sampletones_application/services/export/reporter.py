from typing import Callable, Final, FrozenSet, Optional

from sampletones_application.services.progress import UNMEASURED, StageProgress
from sampletones_application.services.result import ServiceProgress
from sampletones_core.exports.progress import ExportProgress
from sampletones_core.exports.stage import ExportStage

ESTIMATED_STAGES: Final[FrozenSet[ExportStage]] = frozenset(
    {
        ExportStage.WALKING,
        ExportStage.WRITING,
    }
)


class ExportProgressReporter:
    """Carries a format's own account of itself out to whoever is watching the export.

    A run passes through stages counting in units of their own — the song's ticks, the bytes a
    dictionary settles at, the files a batch writes — so each stage is reported against what it
    is measured by and gets a limiter of its own the moment it is first heard from. A stage the
    run never enters is never reported, which is what keeps a bar from being carved into equal
    parts that mean nothing.

    Compressing is the stage with no end to travel toward: it finishes when the song runs out of
    phrases that pay for themselves, so it is measured against the room it has and states no
    remaining time.
    """

    def __init__(
        self,
        emit: Callable[[ServiceProgress[ExportStage]], None],
        withdrawn: Callable[[], bool],
    ) -> None:
        self._emit = emit
        self._withdrawn = withdrawn
        self._stage: Optional[ExportStage] = None
        self._progress: Optional[StageProgress[ExportStage]] = None

    def __call__(self, progress: ExportProgress) -> bool:
        """Reports one stage of the run, and answers whether it goes on.

        Args:
            progress: What the format says it has reached.

        Returns:
            bool: Whether the export is still wanted.
        """
        self._limiter(progress).advance(progress.completed)
        return not self._withdrawn()

    def _limiter(self, progress: ExportProgress) -> StageProgress[ExportStage]:
        if self._progress is None or self._stage != progress.stage:
            self._stage = progress.stage
            self._progress = StageProgress(
                progress.stage,
                UNMEASURED if progress.total is None else progress.total,
                emit=self._emit,
                estimates=progress.stage in ESTIMATED_STAGES,
            )

        return self._progress
