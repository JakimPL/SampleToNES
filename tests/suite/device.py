from typing import Any, Callable, Optional

import numpy as np

from sampletones_core.constants.audio import START_OF_AUDIO


class FakeAudioDevice:
    """The shared output as a player sees it: who holds it, where it stands, and whether it waits.

    It follows `AudioDeviceManager` in the facts a player reads — ownership, the clamped position,
    the pause — so a player's logic runs against it inside the unit suite.
    """

    def __init__(self) -> None:
        self.owner: Optional[Any] = None
        self.paused: bool = False
        self.position: int = START_OF_AUDIO
        self.audio: Optional[np.ndarray] = None

    def set_position_callback(self, _callback: Optional[Callable[[int], None]]) -> None:
        return None

    def replace_audio(self, _audio: np.ndarray, *, owner: Optional[Any] = None) -> bool:
        return False

    def play(
        self,
        audio: np.ndarray,
        *,
        priority: int,
        owner: Optional[Any],
        start: int,
    ) -> bool:
        self.audio = audio
        self.owner = owner
        self.paused = False
        self.position = self._clamped(start)
        return True

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def stop(self) -> None:
        self.owner = None
        self.paused = False
        self.position = START_OF_AUDIO

    def set_position(self, position: int) -> None:
        if self.audio is not None:
            self.position = self._clamped(position)

    def is_owned_by(self, owner: Any) -> bool:
        return owner is not None and self.owner is owner

    def is_paused(self) -> bool:
        return self.paused

    def position_of(self, owner: Any) -> int:
        return self.position if self.is_owned_by(owner) else START_OF_AUDIO

    def _clamped(self, position: int) -> int:
        length = 0 if self.audio is None else len(self.audio)
        return max(START_OF_AUDIO, min(position, length))
