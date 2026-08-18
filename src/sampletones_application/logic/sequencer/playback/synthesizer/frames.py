from dataclasses import dataclass
from itertools import accumulate
from typing import Self, Tuple

from sampletones_core.timing import TickClock


@dataclass(frozen=True)
class RowFrames:
    """Where each of a row's ticks starts and ends within the row's audio.

    A tick clock gives consecutive ticks whole sample counts that sum to their exact span, so the
    lengths within one row vary where the sample rate does not divide the tick rate. Resolving the
    boundaries once per row is what lets every channel write into the same offsets.

    Attributes:
        lengths: The samples each of the row's ticks spans, in order.
        bounds: Each tick's start offset, ending with the row's total length.
    """

    lengths: Tuple[int, ...]
    bounds: Tuple[int, ...]

    @classmethod
    def from_clock(
        cls,
        clock: TickClock,
        *,
        elapsed_ticks: int,
        ticks: int,
    ) -> Self:
        """Resolves the row starting at ``elapsed_ticks`` and spanning ``ticks`` ticks."""
        lengths = tuple(clock.frame_length(elapsed_ticks + tick) for tick in range(ticks))
        return cls(
            lengths=lengths,
            bounds=tuple(accumulate(lengths, initial=0)),
        )

    @property
    def total(self) -> int:
        """The samples the whole row spans."""
        return self.bounds[-1]

    @property
    def longest(self) -> int:
        """The samples the row's longest tick spans."""
        return max(self.lengths, default=0)
