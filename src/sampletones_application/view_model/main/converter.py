from enum import StrEnum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class ConversionPhase(StrEnum):
    IDLE = "idle"
    WAITING = "waiting"
    RUNNING = "running"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ConverterViewModel(BaseModel, frozen=True):
    """Immutable snapshot of converter state for the converter panel.

    Produced by :class:`~sampletones_application.logic.main.converter.ConverterLogic`
    and consumed by
    :class:`~sampletones_application.ui.panels.main.converter.converter.GUIConverterPanel`
    via ``update_view()``.  This is the canonical example of the view-model
    contract: the logic layer produces a complete, self-consistent snapshot;
    the panel only reads it.

    Responsibilities:
    - Carry all data the converter panel needs to render itself: current phase,
      status text, progress fraction, display strings, and the paths being
      processed.
    - Compute derived UI flags as ``@property`` values so that the panel never
      has to duplicate phase-checking logic.

    Governing principles:
    - Frozen: instances are never mutated after construction.  The logic layer
      produces a new instance on each state change and passes it to the panel.
    - Derived flags (``subpanel_visible``, ``convert_button_enabled``,
      ``load_button_enabled``, ``is_done``) must be computed from the stored
      fields, never stored as independent fields that could drift.
    - Must not import from ``ui/``, ``coordinators/``, or ``logic/``.

    Dependencies: ``ConversionPhase``, Pydantic ``BaseModel``.
    """

    phase: ConversionPhase
    status_text: str
    progress: float
    progress_overlay: str
    input_path: Optional[Path]
    output_path: Optional[Path]
    is_file: bool

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
