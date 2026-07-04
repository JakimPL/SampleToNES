from typing import Final

from pydantic import BaseModel

PERCENT_SCALE: Final[int] = 100


class LibraryPanelViewModel(BaseModel, frozen=True):
    status_text: str
    generate_button_label: str
    is_generating: bool
    progress_value: float

    @property
    def progress_overlay(self) -> str:
        """The percentage label rendered over the progress bar, derived from the fraction."""
        fraction = max(0.0, min(1.0, self.progress_value))
        return f"{int(fraction * PERCENT_SCALE)}%"

    @property
    def idle_controls_visible(self) -> bool:
        return not self.is_generating

    @property
    def generating_controls_visible(self) -> bool:
        return self.is_generating
