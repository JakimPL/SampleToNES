from pydantic import BaseModel

from sampletones_application.view_model.shared.percent import format_percent


class LibraryPanelViewModel(BaseModel, frozen=True):
    status_text: str
    generate_button_label: str
    is_generating: bool
    progress_value: float

    @property
    def progress_overlay(self) -> str:
        """The percentage label rendered over the progress bar, derived from the fraction."""
        return format_percent(self.progress_value)

    @property
    def idle_controls_visible(self) -> bool:
        return not self.is_generating

    @property
    def generating_controls_visible(self) -> bool:
        return self.is_generating
