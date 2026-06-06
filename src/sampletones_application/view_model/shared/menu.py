from pydantic import BaseModel


class MenuBarViewModel(BaseModel, frozen=True):
    project_open: bool
    reconstruction_loaded: bool
    play_label: str
    play_or_pause_enabled: bool
    stop_enabled: bool
    autoplay: bool
    fullscreen: bool
    advanced_settings: bool
