from pydantic import BaseModel


class MenuBarViewModel(BaseModel, frozen=True):
    project_open: bool
    reconstruction_loaded: bool
    can_undo: bool
    can_redo: bool
    play_label: str
    play_or_pause_enabled: bool
    stop_enabled: bool
    autoplay: bool
    fullscreen: bool
    advanced_settings: bool

    @property
    def undo_enabled(self) -> bool:
        return self.project_open and self.can_undo

    @property
    def redo_enabled(self) -> bool:
        return self.project_open and self.can_redo
