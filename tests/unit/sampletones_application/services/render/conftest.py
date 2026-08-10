from pathlib import Path
from typing import Callable, Final, List, Optional, Tuple

import numpy as np
import soundfile

from sampletones_core.audio.writers import AudioOutputSpec, WaveOutputSpec
from sampletones_core.project.song_position import SongPosition

SAMPLE_RATE: Final[int] = 44100
ROW_SAMPLES: Final[int] = 735
ROWS: Final[int] = 24
TOTAL_SAMPLES: Final[int] = ROW_SAMPLES * ROWS
LEVEL: Final[float] = 0.25


def wave_spec(sample_rate: int = SAMPLE_RATE) -> AudioOutputSpec:
    return WaveOutputSpec(sample_rate=sample_rate)


class FakeSynthesizer:
    """A kernel that renders a fixed number of identical rows, standing in for a song.

    Each row is a constant level, so a normalising pass has a peak to find and a written file
    can be checked sample by sample without modelling a generator.
    """

    def __init__(
        self,
        *,
        rows: int = ROWS,
        row_samples: int = ROW_SAMPLES,
        level: float = LEVEL,
        on_row: Optional[Callable[[int], None]] = None,
        error: Optional[Exception] = None,
    ) -> None:
        self._rows = rows
        self._row_samples = row_samples
        self._level = level
        self._on_row = on_row
        self._error = error
        self.rendered: int = 0
        self.resets: int = 0
        self.positions: List[Tuple[int, int]] = []

    @property
    def order_position(self) -> int:
        return self.rendered

    @property
    def row_index(self) -> int:
        return 0

    @property
    def is_finished(self) -> bool:
        return self.rendered >= self._rows

    def set_position(self, order_position: int, row_index: int) -> None:
        self.positions.append((order_position, row_index))

    def reset(self) -> None:
        self.resets += 1
        self.rendered = 0

    def render_row(self) -> Tuple[np.ndarray, SongPosition]:
        if self._error is not None and self.rendered == self._rows // 2:
            raise self._error

        if self._on_row is not None:
            self._on_row(self.rendered)

        self.rendered += 1
        row = np.full(self._row_samples, self._level, dtype=np.float32)
        return row, SongPosition()


def read_samples(path: Path) -> np.ndarray:
    audio, _ = soundfile.read(path, dtype="float32")
    return np.asarray(audio, dtype=np.float32)
