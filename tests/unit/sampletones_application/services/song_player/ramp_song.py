import threading
from typing import Final, List, Optional, Sequence, Tuple

import numpy as np

from sampletones_core.project.song_position import SongPosition
from tests.suite.audio.ramp import ramp

ROW: Final[int] = 100
WAIT_SECONDS: Final[float] = 10.0
SYNTHESIS_FAILURE: Final[str] = "The synthesizer failed"


class RampSong:
    """A synthesizer whose rows are runs of the ramp, each order holding rows of one length.

    A row continues the ramp from where the rows before it in the song end, so what a source read back
    states the song samples it played. A row the case names fails, and ``held`` keeps the render thread
    before the row it names until the case lets it go.
    """

    def __init__(self, orders: Sequence[int], *, rows: int, failing: Optional[SongPosition] = None) -> None:
        self._orders = list(orders)
        self._rows = rows
        self._failing = failing
        self._order_position: int = 0
        self._row_index: int = 0
        self.resets: int = 0
        self.rates: List[int] = []
        self.held: Optional[SongPosition] = None
        self.reached = threading.Event()
        self.release = threading.Event()

    @property
    def order_position(self) -> int:
        return self._order_position

    @property
    def row_index(self) -> int:
        return self._row_index

    @property
    def is_finished(self) -> bool:
        return self._order_position >= len(self._orders)

    def set_position(self, order_position: int, row_index: int) -> None:
        self._order_position = order_position
        self._row_index = row_index

    def reset(self) -> None:
        self.resets += 1

    def render_row(self) -> Tuple[np.ndarray, SongPosition]:
        position = SongPosition(order_position=self._order_position, row_index=self._row_index)
        if position == self.held:
            self.reached.set()
            self.release.wait(timeout=WAIT_SECONDS)

        if position == self._failing:
            raise RuntimeError(SYNTHESIS_FAILURE)

        start = (self._order_position * self._rows + self._row_index) * ROW
        self._row_index += 1
        if self._row_index >= self._rows:
            self._order_position += 1
            self._row_index = 0

        return ramp(ROW, start=start), position

    def factory(self, sample_rate: int) -> "RampSong":
        self.rates.append(sample_rate)
        return self
