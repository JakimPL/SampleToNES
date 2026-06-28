from pydantic import BaseModel


class LibraryPanelViewModel(BaseModel, frozen=True):
    status_text: str
    generate_button_label: str
    is_generating: bool
    progress_value: float
    progress_overlay: str

    @property
    def idle_controls_visible(self) -> bool:
        return not self.is_generating

    @property
    def generating_controls_visible(self) -> bool:
        return self.is_generating
