from math import copysign
from typing import Callable, Final, Optional

from sampletones_application.ui.panels.sequencer.grid.scroll.axis import ScrollAxis
from sampletones_application.ui.panels.sequencer.grid.scroll.band import TravelBand

TRAVEL_FLOOR_CELLS_PER_SECOND: Final[float] = 6.0
TRAVEL_CEILING_CELLS_PER_SECOND: Final[float] = 45.0
TRAVEL_FULL_PACE_OVERSHOOT_CELLS: Final[float] = 5.0


class DragTravel:
    """Carries a grid's view along while a held pointer stands past the band drawn on screen.

    A held pointer keeps reporting for as long as the button is down, wherever it has been carried
    to, so the travel runs from that report and paces itself by the frame's own duration: the same
    stretch of grid passes under the pointer however fast the frames arrive. Each step is added to
    the offset last issued, because a table reports the scroll it was drawn with rather than the one
    just set — reading it back would have the travel re-issue an offset it has already reached.
    """

    def __init__(
        self,
        *,
        axis: ScrollAxis,
        band: Callable[[], Optional[TravelBand]],
        elapsed: Callable[[], float],
    ) -> None:
        self._axis = axis
        self._band = band
        self._elapsed = elapsed
        self._offset: Optional[float] = None

    def advance(self) -> None:
        """Travels one frame's worth toward whatever the pointer stands past, up to the grid's end.

        A pointer standing within the band leaves the grid where it is, and the drag then reaches
        the cell it stands on the way it always has. A grid awaiting its first layout states no
        band, and one that fits on screen has nowhere to travel to.
        """
        band = self._band()
        if band is None:
            self.rest()
            return

        scroll_max = self._axis.scroll_max()
        if scroll_max <= 0.0:
            self.rest()
            return

        drawn = self._axis.scroll()
        overshoot = self._overshoot(band, drawn, scroll_max)
        if overshoot == 0.0:
            self.rest()
            return

        travel = self._pace(overshoot, band.cell_extent) * band.cell_extent * self._elapsed()
        offset = self._offset if self._offset is not None else drawn
        self._offset = min(max(offset + copysign(travel, overshoot), 0.0), scroll_max)
        self._axis.set_scroll(self._offset)

    def rest(self) -> None:
        """Ends the travel, so the next one sets out from the offset the grid is drawn with."""
        self._offset = None

    def _overshoot(
        self,
        band: TravelBand,
        drawn: float,
        scroll_max: float,
    ) -> float:
        """How far past the band the pointer stands, reading negative before its near edge.

        The band begins where the first cell's edge stands once the scroll carrying it is added
        back, and it holds what the grid lays out less what it still has to scroll away.
        """
        near = band.first_edge + drawn
        far = near + band.cell_count * band.cell_extent - scroll_max
        pointer = self._axis.pointer()
        if pointer < near:
            return pointer - near

        if pointer > far:
            return pointer - far

        return 0.0

    @staticmethod
    def _pace(overshoot: float, cell_extent: float) -> float:
        """How many cells a second the travel runs at: a floor at the edge, rising to a ceiling.

        The pace answers how far past the edge the pointer is carried, so a reader nudging the edge
        creeps along and one reaching well past it covers the grid.
        """
        reach = min(abs(overshoot) / (cell_extent * TRAVEL_FULL_PACE_OVERSHOOT_CELLS), 1.0)
        span = TRAVEL_CEILING_CELLS_PER_SECOND - TRAVEL_FLOOR_CELLS_PER_SECOND
        return TRAVEL_FLOOR_CELLS_PER_SECOND + span * reach
