from typing import FrozenSet, Protocol, Tuple

import numpy as np

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.song_position import SongPosition


class RowSynthesizerProtocol(Protocol):
    """Streaming synthesis kernel the song-player service drives, one row at a time.

    This is the service's input contract; the concrete synthesiser lives in the logic layer
    and satisfies it structurally. Each ``render_row`` call produces one row's worth of audio
    (ticks_per_row × frame_length samples), advances the internal position cursor, and returns
    a snapshot of the cursor from before the advance so callers can post accurate position events.
    """

    @property
    def order_position(self) -> int: ...

    @property
    def row_index(self) -> int: ...

    @property
    def is_finished(self) -> bool: ...

    def set_position(self, order_position: int, row_index: int) -> None: ...

    def set_channel_mask(self, active_channels: FrozenSet[GeneratorName]) -> None: ...

    def render_row(self) -> Tuple[np.ndarray, SongPosition]: ...

    def reset(self) -> None: ...
