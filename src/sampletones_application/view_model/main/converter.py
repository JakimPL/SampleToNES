from enum import StrEnum
from pathlib import Path
from typing import Final, FrozenSet, Optional

from pydantic import BaseModel

from sampletones_application.view_model.shared.percent import format_percent


class ConversionPhase(StrEnum):
    IDLE = "idle"
    WAITING = "waiting"
    RUNNING = "running"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ConverterAction(StrEnum):
    """The single action the panel's button offers in the current phase.

    Every terminal phase returns to idle on its own, so the button only ever
    starts a conversion or cancels the running one.
    """

    CONVERT = "convert"
    CANCEL = "cancel"


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
    input_path: Optional[Path]
    output_path: Optional[Path]
    is_file: bool
    other_operation_active: bool

    @property
    def progress_overlay(self) -> str:
        """The percentage label rendered over the progress bar, derived from the fraction."""
        return format_percent(self.progress)

    @property
    def is_active(self) -> bool:
        return self.phase in ACTIVE_PHASES

    @property
    def subpanel_visible(self) -> bool:
        return self.phase != ConversionPhase.IDLE

    @property
    def convert_button_enabled(self) -> bool:
        return self.phase == ConversionPhase.IDLE and self.input_path is not None and not self.other_operation_active

    @property
    def primary_action(self) -> ConverterAction:
        """Cancel while a conversion occupies resources, otherwise convert.

        Terminal phases resolve back to idle on their own, so they present the
        convert action (disabled until the phase is actually idle)."""
        return ConverterAction.CANCEL if self.is_active else ConverterAction.CONVERT

    @property
    def primary_action_enabled(self) -> bool:
        if self.primary_action == ConverterAction.CANCEL:
            return self.phase != ConversionPhase.CANCELLING

        return self.convert_button_enabled
