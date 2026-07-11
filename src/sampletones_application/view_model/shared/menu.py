from pydantic import BaseModel


class MenuBarViewModel(BaseModel, frozen=True):
    project_open: bool
    reconstruction_loaded: bool
    reconstruction_saveable: bool
    reconstruction_in_project: bool
    reconstruction_file_backed: bool
    reconstruction_audio_recorded: bool
    can_undo: bool
    can_redo: bool
    play_label: str
    play_or_pause_enabled: bool
    pause_enabled: bool
    player_paused: bool
    stop_enabled: bool
    autoplay: bool
    follow_playback: bool
    loop_song: bool
    fullscreen: bool
    advanced_settings: bool

    @property
    def undo_enabled(self) -> bool:
        return self.project_open and self.can_undo

    @property
    def redo_enabled(self) -> bool:
        return self.project_open and self.can_redo

    @property
    def add_to_sequencer_enabled(self) -> bool:
        """Adding the loaded reconstruction needs an open project that does not already hold it."""
        return self.reconstruction_loaded and self.project_open and not self.reconstruction_in_project

    @property
    def open_in_explorer_enabled(self) -> bool:
        """Revealing the reconstruction file needs a reconstruction that is backed by one."""
        return self.reconstruction_loaded and self.reconstruction_file_backed

    @property
    def locate_audio_enabled(self) -> bool:
        """Locating the original audio needs a recorded path to point the file manager at."""
        return self.reconstruction_loaded and self.reconstruction_audio_recorded
