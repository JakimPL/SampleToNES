import threading
from collections import deque
from dataclasses import dataclass
from typing import Deque, Generic, List, Tuple

import numpy as np

from .source import ReportT, Tagged


@dataclass(frozen=True)
class Taken(Generic[ReportT]):
    """What one take moved into a block: its frames, the rows it completed, and whether the buffer was closed.

    A take fills its block whole until the producer has ended, so a take shorter than its block is the last.
    A closed buffer leaves the block as it was, which tells a stop apart from the end of the rows.

    Attributes:
        frames: The frames written into the block, from its start.
        reports: The report of every row whose last sample the block holds, at the offset just past it.
        closed: Whether the buffer was closed, which leaves the block untouched.
    """

    frames: int
    reports: Tuple[Tagged[ReportT], ...]
    closed: bool


@dataclass
class _Row(Generic[ReportT]):
    samples: np.ndarray
    report: ReportT
    taken: int


class PrefetchBuffer(Generic[ReportT]):
    """Rows rendered ahead of the device, bounded by the samples they hold, handed out in blocks of any length.

    A producer puts rows in while fewer than ``capacity`` samples wait, and waits while that many do. A row
    longer than the whole capacity goes in once the buffer has room, so a row of any length plays. The writer
    takes blocks out across rows and waits while too few samples wait, so the producer's pace and the device's
    pace meet here. Each row's report goes out with the block holding its last sample.

    Closing wakes both sides at once: a put then answers that the buffer is closed, and so does a take, which
    tells a stop apart from the end of the rows.
    """

    def __init__(self, *, capacity: int) -> None:
        """Holds the bound on the samples waiting.

        Args:
            capacity: The samples the buffer holds ahead, which must be at least one.

        Raises:
            ValueError: If ``capacity`` is below one.
        """
        if capacity < 1:
            raise ValueError(f"A prefetch buffer holds at least one sample, not {capacity}")

        self._capacity = capacity
        self._condition = threading.Condition()
        self._rows: Deque[_Row[ReportT]] = deque()
        self._queued: int = 0
        self._ended: bool = False
        self._closed: bool = False

    @property
    def queued(self) -> int:
        """How many samples wait to be taken."""
        with self._condition:
            return self._queued

    def put(self, samples: np.ndarray, report: ReportT) -> bool:
        """Adds a row once the buffer has room for it, waiting while it is full.

        Returns:
            bool: Whether the row went in, which a closed buffer refuses.
        """
        with self._condition:
            self._condition.wait_for(lambda: self._closed or self._queued < self._capacity)
            if self._closed:
                return False

            self._rows.append(_Row(samples=samples, report=report, taken=0))
            self._queued += len(samples)
            self._condition.notify_all()
            return True

    def end(self) -> None:
        """Tells the writer the rows have ended, so a take hands out what waits and then comes up short."""
        with self._condition:
            self._ended = True
            self._condition.notify_all()

    def close(self) -> None:
        """Wakes both sides and refuses every later put and take."""
        with self._condition:
            self._closed = True
            self._rows.clear()
            self._queued = 0
            self._condition.notify_all()

    def take_into(self, block: np.ndarray) -> Taken[ReportT]:
        """Fills ``block`` from the rows waiting, waiting while too few samples wait and the producer goes on."""
        with self._condition:
            self._condition.wait_for(lambda: self._closed or self._ended or self._queued >= len(block))
            if self._closed:
                return Taken(frames=0, reports=(), closed=True)

            frames, reports = self._move_into(block)
            self._queued -= frames
            self._condition.notify_all()
            return Taken(frames=frames, reports=reports, closed=False)

    def _move_into(self, block: np.ndarray) -> Tuple[int, Tuple[Tagged[ReportT], ...]]:
        """Moves samples into ``block`` row after row, reporting each row it completes. The caller holds the lock."""
        frames = 0
        reports: List[Tagged[ReportT]] = []
        while self._rows and frames < len(block):
            row = self._rows[0]
            count = min(len(block) - frames, len(row.samples) - row.taken)
            block[frames : frames + count] = row.samples[row.taken : row.taken + count]
            frames += count
            row.taken += count
            if row.taken == len(row.samples):
                self._rows.popleft()
                reports.append(Tagged(offset=frames, report=row.report))

        return frames, tuple(reports)
