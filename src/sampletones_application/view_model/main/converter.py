from enum import StrEnum
from pathlib import Path
from typing import Final, FrozenSet, Optional

from pydantic import BaseModel


class ConversionPhase(StrEnum):
    IDLE = "idle"
    WAITING = "waiting"
    RUNNING = "running"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


ACTIVE_PHASES: Final[FrozenSet[ConversionPhase]] = frozenset(
    {
        ConversionPhase.WAITING,
        ConversionPhase.RUNNING,
        ConversionPhase.CANCELLING,
    }
)


class ConverterViewModel(BaseModel, frozen=True):
    """
    An immutable snapshot of converter state that defines what the panel is allowed to know.

    Derived UI flags are computed properties, not stored fields — the phase is
    the single source of truth and the view model is always self-consistent by
    construction.
    """

    phase: ConversionPhase
    status_text: str
    progress: float
    progress_overlay: str
    input_path: Optional[Path]
    output_path: Optional[Path]
    is_file: bool

    @property
    def is_active(self) -> bool:
        return self.phase in ACTIVE_PHASES

    @property
    def subpanel_visible(self) -> bool:
        return self.phase != ConversionPhase.IDLE

    @property
    def convert_button_enabled(self) -> bool:
        return self.phase == ConversionPhase.IDLE and self.input_path is not None

    @property
    def load_button_enabled(self) -> bool:
        return self.phase == ConversionPhase.COMPLETED and self.output_path is not None

    @property
    def is_done(self) -> bool:
        return self.phase in (
            ConversionPhase.COMPLETED,
            ConversionPhase.CANCELLED,
            ConversionPhase.FAILED,
        )
