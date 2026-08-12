from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, Optional, Self, TypeVar

CursorT = TypeVar("CursorT")
RegionT = TypeVar("RegionT")


@dataclass(frozen=True)
class GridInputState(ABC, Generic[CursorT, RegionT]):
    """Edit cursor, pending entry and selection anchor of a sequencer grid.

    The anchor is where a range selection was started; the cursor is its other end, so the two
    together are the region a block operation acts on. Every plain move builds a state without
    one, which is what makes a move collapse a selection to the cell it lands in.

    A grid states how a pair of its own cells bounds a block and how a block reaches a cell; the
    selection rules that follow from those two are stated here and serve every grid.
    """

    cursor: Optional[CursorT] = None
    pending: str = ""
    anchor: Optional[CursorT] = None

    @abstractmethod
    def _region_between(self, first: CursorT, second: CursorT) -> RegionT:
        """The block a pair of cells bounds, whichever way round the pair stands."""

    @abstractmethod
    def _covers(self, region: RegionT, cell: CursorT) -> bool:
        """Whether ``region`` reaches ``cell``."""

    def reset_pending(self) -> Self:
        """Drops a partial entry, leaving the cursor and any selection where they stand.

        The anchor survives because this runs before every move, the extending ones included:
        each gesture then decides whether to hold the selection or collapse it.
        """
        return type(self)(cursor=self.cursor, pending="", anchor=self.anchor)

    def collapse(self) -> Self:
        """Drops the selection, leaving the cursor's own cell as the whole target."""
        return type(self)(cursor=self.cursor, pending=self.pending)

    @property
    def region(self) -> Optional[RegionT]:
        """The block a selection covers, once one has been started."""
        if self.cursor is None or self.anchor is None:
            return None

        return self._region_between(self.anchor, self.cursor)

    def region_at(self, cell: CursorT) -> RegionT:
        """The block a gesture raised on ``cell`` acts on: the selection it stands in, or the cell
        alone.

        A gesture raised inside a selection acts on the whole of it, which is what a reader who has
        just dragged a range out expects it to reach; one raised anywhere else acts on the cell it
        names, which is a block of exactly that cell. A cursor with nothing selected therefore
        stands on a block of one cell, so copying reaches the cell the reader is working in and
        needs no selection made first.
        """
        region = self.region
        if region is not None and self._covers(region, cell):
            return region

        return self._region_between(cell, cell)

    def extend_to(self, cursor: CursorT) -> Self:
        """Carries the moving end of the selection to ``cursor``, anchoring it where it began.

        A selection that has not been started yet takes the cell the cursor stands on as its
        anchor, so the first extending gesture selects the cell it came from as well as the one
        it reaches.
        """
        return type(self)(
            cursor=cursor,
            pending="",
            anchor=self.anchor if self.anchor is not None else self.cursor,
        )

    def cancel(self) -> Self:
        """Drops a partial entry and any selection, which is what Escape asks of a grid."""
        return self.collapse().reset_pending()

    def _after_entry(self) -> Self:
        """The state a committed entry leaves: the cursor alone, nothing pending and nothing selected.

        Typing writes the one cell the cursor stands on, so it takes the selection down to that
        cell instead of leaving a range for the next gesture to act on.
        """
        return self.collapse().reset_pending()
