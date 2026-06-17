from pydantic import BaseModel


class SongPlayerViewModel(BaseModel, frozen=True):
    is_loaded: bool
    is_playing: bool
    is_paused: bool
    order_position: int
    row_index: int

    @property
    def play_enabled(self) -> bool:
        return self.is_loaded

    @property
    def stop_enabled(self) -> bool:
        return self.is_loaded and self.is_playing
