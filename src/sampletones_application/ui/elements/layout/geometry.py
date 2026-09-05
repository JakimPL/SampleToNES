from dataclasses import dataclass
from typing import Final, Tuple

Window = Tuple[int, int]

GEOMETRY_TOLERANCE: Final[float] = 1.0
UNMEASURED: Final[float] = 0.0
ONE_ROW: Final[int] = 1


@dataclass
class RowGeometry:
    """The room one row takes, read from the rows a list has drawn.

    A region showing part of a long list decides two things from this: how many rows its height
    holds, and which of them a scroll position reaches. Both are properties of the theme and the
    font a row is drawn under rather than of any one list, so the reading is taken from whatever
    rows have already been placed and shared by every region drawing rows of that shape. A folder
    opens knowing what a row takes because the list the folder stands in measured it.

    A geometry that has yet to read anything holds every row in its window, which draws a list
    whole and gives the next frame something to measure.

    ``overscan`` is how many rows stand beyond each edge of what a region shows, so a scroll in
    either direction meets rows that are already there.
    """

    overscan: int
    pitch: float

    @classmethod
    def unmeasured(cls, *, overscan: int) -> "RowGeometry":
        """The reading a list starts from, before it has drawn a row to measure."""
        return cls(overscan=overscan, pitch=UNMEASURED)

    @property
    def measured(self) -> bool:
        """Whether a reading has been taken, which is what lets a region hold rows back."""
        return self.pitch > UNMEASURED

    def size(self, height: float) -> int:
        """How many rows a window over a region of this height holds, overscan included."""
        showing = max(ONE_ROW, int(height / self.pitch) + ONE_ROW)
        return showing + 2 * self.overscan

    def windows(self, *, height: float, total: int) -> bool:
        """Whether a list of this length outgrows the region, which is what asks for a window."""
        return self.measured and total > self.size(height)

    def slice_of(self, *, offset: float, height: float, total: int) -> Window:
        """The rows a scroll position reaches: where the window opens, and how many it holds."""
        if not self.windows(height=height, total=total):
            return (0, total)

        count = self.size(height)
        reached = int(offset / self.pitch)
        return (max(0, min(reached - self.overscan, total - count)), count)

    def reserve(self, rows: int) -> int:
        """The room a number of rows takes, which stands in place of the ones left undrawn."""
        return int(rows * self.pitch)

    def take(self, *, block: float, rows: int) -> bool:
        """Read what a row takes from a block of drawn rows, reporting a reading worth redrawing.

        The block is measured whole rather than row by row, so whatever a table lays around its
        rows is carried by the same number that reserves room for them. A move worth a pixel is
        worth drawing again.
        """
        if rows <= 0 or block <= UNMEASURED:
            return False

        pitch = block / rows
        moved = abs(pitch - self.pitch) > GEOMETRY_TOLERANCE
        self.pitch = pitch
        return moved
