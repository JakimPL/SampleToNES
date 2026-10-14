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
    case holds the synthesis back or fails it. Every playback renders through a cursor of its own, which
    ``synthesizer`` builds the way the application builds a synthesizer per playback.
    """

    def __init__(self, orders: Sequence[Sequence[int]]) -> None:
        self._lock = threading.Lock()
        self._orders: List[Tuple[int, ...]] = []
        self._starts: List[Tuple[int, ...]] = []
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

    def synthesizer(self, _sample_rate: int) -> "SongCursor":
        """A cursor of its own for one playback of the song."""
        return SongCursor(self)

    def orders(self) -> int:
        with self._lock:
            return len(self._orders)

    def rows_in(self, order_position: int) -> int:
        with self._lock:
            return len(self._orders[order_position])

    def row(self, position: SongPosition) -> np.ndarray:
        """The samples one row holds, running the ramp on from the rows before it."""
        with self._lock:
            frames = self._orders[position.order_position][position.row_index]
            start = self._starts[position.order_position][position.row_index]

        return ramp(frames, start=start)


class SongCursor:
    """Where one playback of a scripted song stands, rendered row by row."""

    def __init__(self, song: ScriptedSong) -> None:
        self._song = song
        self._order_position: int = 0
        self._row_index: int = 0

    @property
    def order_position(self) -> int:
        return self._order_position

    @property
    def row_index(self) -> int:
        return self._row_index

    @property
    def is_finished(self) -> bool:
        return self._order_position >= self._song.orders()

    def set_position(self, order_position: int, row_index: int) -> None:
        self._order_position = order_position
        self._row_index = row_index

    def reset(self) -> None:
        return None

    def render_row(self) -> Tuple[np.ndarray, SongPosition]:
        position = SongPosition(order_position=self._order_position, row_index=self._row_index)
        hook = self._song.before_render
        if hook is not None:
            hook(position)

        samples = self._song.row(position)
        self._row_index += 1
        if self._row_index >= self._song.rows_in(position.order_position):
            self._order_position += 1
            self._row_index = 0

        return samples, position
