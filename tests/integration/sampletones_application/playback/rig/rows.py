import threading
from typing import Final

from sampletones_core.project.song_position import SongPosition

ROW_SECONDS: Final[float] = 10.0
SYNTHESIS_FAILURE: Final[str] = "The synthesizer failed"


class HeldRow:
    """A row the song's synthesizer holds back until the case lets it render, as a synthesizer slower than
    real time does.

    A row the case never lets render gives way after ``ROW_SECONDS``, so a forgotten hold ends as a thread that
    outlived the case and not as a hang.
    """

    def __init__(self, row: SongPosition) -> None:
        self._row = row
        self.reached = threading.Event()
        self.render = threading.Event()

    def __call__(self, position: SongPosition) -> None:
        if position == self._row:
            self.reached.set()
            self.render.wait(timeout=ROW_SECONDS)


class FailingRow:
    """A row the song's synthesizer fails once the case lets it, so the failure lands where the case wants it."""

    def __init__(self, row: SongPosition) -> None:
        self._row = row
        self.reached = threading.Event()
        self.fail = threading.Event()

    def __call__(self, position: SongPosition) -> None:
        if position != self._row:
            return

        self.reached.set()
        self.fail.wait(timeout=ROW_SECONDS)
        raise RuntimeError(SYNTHESIS_FAILURE)
