from enum import StrEnum
from typing import Final, FrozenSet, Optional, Tuple

from pydantic import BaseModel

from sampletones_application.view_model.shared.percent import format_percent
from sampletones_core.exports.stage import ExportStage

NO_PROGRESS: Final[float] = 0.0
NOTHING_MEASURED: Final[int] = 0


class ExportPhase(StrEnum):
    IDLE = "idle"
    EXPORTING = "exporting"
    CANCELLING = "cancelling"


ACTIVE_PHASES: Final[FrozenSet[ExportPhase]] = frozenset(
    {
        ExportPhase.EXPORTING,
        ExportPhase.CANCELLING,
    }
)


class SongExportViewModel(BaseModel, frozen=True):
    """What the export dialog draws: the stages a run has reached, and where the latest one is.

    A run's shape is its format's own — a tracker instrument is written and done with, while a
    program is played out, compressed and then written — so the stages are listed as they are
    reached rather than laid out in advance. The one at the end of the list is the one under way,
    and the stages before it are behind.

    Attributes:
        phase: Where the run stands, from the dialog opening to the outcome that closes it.
        stages: The stages the run has reached, in the order it reached them.
        figure: What the stage under way has covered, in the words its own unit is stated in.
        progress: How far the stage under way has got, from 0 to 1, where it travels to an end.
        travelling: Whether the stage under way arrives at what it is measured against.
    """

    phase: ExportPhase
    stages: Tuple[ExportStage, ...]
    figure: str
    progress: float
    travelling: bool

    @classmethod
    def idle(cls) -> "SongExportViewModel":
        """The dialog with no run behind it, which is what the window opens on."""
        return cls(
            phase=ExportPhase.IDLE,
            stages=(),
            figure="",
            progress=NO_PROGRESS,
            travelling=False,
        )

    @property
    def is_active(self) -> bool:
        return self.phase in ACTIVE_PHASES

    @property
    def stage(self) -> Optional[ExportStage]:
        """The stage under way, and ``None`` before the run names its first."""
        return self.stages[-1] if self.stages else None

    @property
    def progress_visible(self) -> bool:
        """Whether a bar stands, which a stage arriving at an end is what earns."""
        return self.travelling

    @property
    def working_visible(self) -> bool:
        """Whether the turning indicator stands, which is how a stage without an end reads."""
        return not self.travelling

    @property
    def progress_overlay(self) -> str:
        """The percentage label rendered over the progress bar, derived from the fraction."""
        return format_percent(self.progress)

    @property
    def cancel_enabled(self) -> bool:
        """Whether a running export still takes a stop, which one already stopping has taken."""
        return self.phase == ExportPhase.EXPORTING

    def stage_visible(self, stage: ExportStage) -> bool:
        """Whether ``stage`` is listed, which the run reaching it is what decides."""
        return stage in self.stages

    def stage_reached(self, stage: ExportStage) -> bool:
        """Whether ``stage`` is behind the run, which is what dims it in the list."""
        return self.stage_visible(stage) and stage != self.stage
