from enum import StrEnum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from ....constants.main import (
    LBL_BUTTON_MAIN_CONVERTER_CANCEL,
    LBL_BUTTON_MAIN_CONVERTER_CLOSE,
    LBL_BUTTON_MAIN_CONVERTER_CONVERT_DIRECTORY,
    LBL_BUTTON_MAIN_CONVERTER_CONVERT_SAMPLE,
)


class ConversionPhase(StrEnum):
    IDLE = "idle"
    WAITING = "waiting"
    RUNNING = "running"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ConverterViewModel(BaseModel, frozen=True):
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
        return self.phase in (ConversionPhase.COMPLETED, ConversionPhase.CANCELLED, ConversionPhase.FAILED)

    @property
    def cancel_button_label(self) -> str:
        return LBL_BUTTON_MAIN_CONVERTER_CLOSE if self.is_done else LBL_BUTTON_MAIN_CONVERTER_CANCEL

    @property
    def convert_button_label(self) -> str:
        base = LBL_BUTTON_MAIN_CONVERTER_CONVERT_SAMPLE if self.is_file else LBL_BUTTON_MAIN_CONVERTER_CONVERT_DIRECTORY
        if self.input_path is not None:
            return f"{base}: {self.input_path.name}"

        return base
