from dataclasses import dataclass


@dataclass(frozen=True)
class TravelBand:
    """Where a grid's cells stand along the axis it scrolls, and how many of them it lays out.

    ``first_edge`` is the leading edge of the first cell in the coordinates the viewport is drawn
    in, which travels with the scroll: adding the scroll back to it gives the edge the band on
    screen begins at.
    """

    first_edge: float
    cell_extent: float
    cell_count: int
