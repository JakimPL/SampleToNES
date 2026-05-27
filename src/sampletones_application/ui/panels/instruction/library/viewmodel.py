from pydantic import BaseModel


class LibraryPanelViewModel(BaseModel, frozen=True):
    status_text: str
    generate_button_label: str
    generate_button_enabled: bool
    generate_button_visible: bool
    progress_visible: bool
    progress_value: float
    progress_overlay: str
