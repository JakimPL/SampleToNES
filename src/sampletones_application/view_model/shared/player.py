from pydantic import BaseModel


class PlayerViewModel(BaseModel, frozen=True):
    has_audio: bool
    is_playing: bool
    is_paused: bool
    current_position: int
    total_samples: int
