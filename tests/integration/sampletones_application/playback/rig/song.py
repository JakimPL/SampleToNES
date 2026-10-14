import itertools
import threading
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np

from sampletones_core.project.song_position import SongPosition
from tests.suite.audio.ramp import ramp

RenderHook = Callable[[SongPosition], None]


class ScriptedSong:
    """A song whose rows are runs of the ramp, rendered row by row the way the synthesizer renders a project.

    Each order holds rows of the lengths it is given. A row continues the ramp from where the rows before it
    in the song end, so what the device received reads back as the song samples it played, and a seek shows
    as a jump in the indices. ``before_render`` runs on the render thread before each row, which is where a
    case holds the synthesis back or fails it.
    """

    def __init__(self, orders: Sequence[Sequence[int]]) -> None:
        self._lock = threading.Lock()
        self._orders: List[Tuple[int, ...]] = []
        self._starts: List[Tuple[int, ...]] = []
        self._order_position: int = 0
        self._row_index: int = 0
        self.before_render: Optional[RenderHook] = None
        self.compose(orders)

    def compose(self, orders: Sequence[Sequence[int]]) -> None:
        """Gives the song new orders, each a sequence of row lengths in samples."""
        rows = [tuple(order) for order in orders]
        lengths = [length for order in rows for length in order]
        starts = iter(itertools.accumulate(lengths, initial=0))
        with self._lock:
            self._orders = rows
            self._starts = [tuple(next(starts) for _ in order) for order in rows]

    def start_of(self, position: SongPosition) -> int:
        """The song sample a row begins at, which its first ramp value states."""
        with self._lock:
            return self._starts[position.order_position][position.row_index]

    @property
    def length(self) -> int:
        """How many samples a pass through the whole song spans."""
        with self._lock:
            return sum(sum(order) for order in self._orders)

    @property
    def order_position(self) -> int:
        with self._lock:
            return self._order_position

    @property
    def row_index(self) -> int:
        with self._lock:
            return self._row_index

    @property
    def is_finished(self) -> bool:
        with self._lock:
            return self._order_position >= len(self._orders)

    def set_position(self, order_position: int, row_index: int) -> None:
        with self._lock:
            self._order_position = order_position
            self._row_index = row_index

    def reset(self) -> None:
        return None

    def render_row(self) -> Tuple[np.ndarray, SongPosition]:
        with self._lock:
            position = SongPosition(order_position=self._order_position, row_index=self._row_index)

        if self.before_render is not None:
            self.before_render(position)

        with self._lock:
            frames = self._orders[position.order_position][position.row_index]
            start = self._starts[position.order_position][position.row_index]
            self._advance(position)

        return ramp(frames, start=start), position

    def _advance(self, position: SongPosition) -> None:
        """Moves past the row just rendered, onto the next order once the row ends its own.

        A seek made while the row rendered stands, since the cursor already names where the song goes next.
        The caller holds the lock.
        """
        if (self._order_position, self._row_index) != (position.order_position, position.row_index):
            return

        self._row_index += 1
        if self._row_index >= len(self._orders[self._order_position]):
            self._order_position += 1
            self._row_index = 0
