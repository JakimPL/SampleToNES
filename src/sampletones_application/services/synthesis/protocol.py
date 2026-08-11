from typing import Protocol, Tuple

import numpy as np

from sampletones_core.project.song_position import SongPosition


class RowSynthesizerProtocol(Protocol):
    """Streaming synthesis kernel a service drives, one row at a time.

    This is the input contract every consumer of a song's audio takes; the concrete synthesiser
    lives in the logic layer and satisfies it structurally. Each ``render_row`` call produces one
    row's worth of audio, advances the internal position cursor, and returns a snapshot of the
    cursor from before the advance so callers can post accurate position events.

    The player and the renderer drive the same kernel through this one contract, which is what
    makes a rendered file sound like what playback produces: the synthesis code is written once.
    """

    @property
    def order_position(self) -> int: ...

    @property
    def row_index(self) -> int: ...

    @property
    def is_finished(self) -> bool: ...

    def set_position(self, order_position: int, row_index: int) -> None: ...

    def render_row(self) -> Tuple[np.ndarray, SongPosition]: ...

    def reset(self) -> None: ...
