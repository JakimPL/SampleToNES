from dataclasses import dataclass
from typing import Final, Tuple

Window = Tuple[int, int]

GEOMETRY_TOLERANCE: Final[float] = 1.0
UNMEASURED: Final[float] = 0.0
ONE_ROW: Final[int] = 1
MINIMUM_ROW_PITCH: Final[float] = 8.0


@dataclass
class RowGeometry:
    """The room one row takes, read from the rows a list has drawn.

    A region showing part of a long list decides two things from this: how many rows its height
    holds, and which of them a scroll position reaches. Both are properties of the theme and the
    font a row is drawn under rather than of any one list, so the reading is taken from whatever
    rows have already been placed and shared by every region drawing rows of that shape. A folder
    opens knowing what a row takes because the list the folder stands in measured it.

    A geometry that has yet to read anything works from the least room a row can take, so a first
    draw is generous rather than unbounded: it builds more rows than it needs, measures them, and
    holds to that reading from the next frame on.

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
        """Whether a reading has been taken, which is what a region's own room is held to."""
        return self.pitch > UNMEASURED

    @property
    def room(self) -> float:
        """The room one row is worked from: what was read, or the least a row can take.

        ``MINIMUM_ROW_PITCH`` is a floor rather than a guess at the theme in force, so a window
        taken before anything has been measured is wider than it needs to be and never narrower.
        """
        return self.pitch if self.measured else MINIMUM_ROW_PITCH

    def size(self, height: float) -> int:
        """How many rows a window over a region of this height holds, overscan included."""
        showing = max(ONE_ROW, int(height / self.room) + ONE_ROW)
        return showing + 2 * self.overscan

    def windows(self, *, height: float, total: int) -> bool:
        """Whether a list of this length outgrows the region, which is what asks for a window."""
        return total > self.size(height)

    def slice_of(self, *, offset: float, height: float, total: int) -> Window:
        """The rows a scroll position reaches: where the window opens, and how many it holds.

        The window opens where the offset stands counted in the same rooms the undrawn rows are
        reserved in, so the block a region builds covers the position it was chosen for whatever
        the reading of a row stands at. The overscan above it is what a scroll back the way it
        came meets, and the end of the list is what a region scrolled past its last window holds.
        """
        if not self.windows(height=height, total=total):
            return (0, total)

        count = self.size(height)
        reached = int(offset / self.room) - self.overscan
        return (max(0, min(reached, total - count)), count)

    def reserve(self, rows: int) -> int:
        """The room a number of rows takes, which stands in place of the ones left undrawn."""
        return int(rows * self.room)

    def take(self, *, block: float, rows: int) -> bool:
        """Read what a row takes from a block of drawn rows, reporting a reading worth redrawing.

        The block is measured whole rather than row by row, so whatever a table lays around its
        rows is carried by the same number that reserves room for them. A move worth a pixel is
        worth drawing again.

        A block giving less than ``MINIMUM_ROW_PITCH`` a row was measured while its rows stood
        clipped or unplaced, since no theme draws a row that small. The reading already taken is
        kept, and the answer is that nothing moved.
        """
        if rows <= 0:
            return False

        pitch = block / rows
        if pitch < MINIMUM_ROW_PITCH:
            return False

        moved = abs(pitch - self.pitch) > GEOMETRY_TOLERANCE
        self.pitch = pitch
        return moved
