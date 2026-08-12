from typing import List, Optional, Tuple

import pytest

from sampletones_application.ui.panels.sequencer.grid.scroll.band import TravelBand
from sampletones_application.ui.panels.sequencer.grid.scroll.travel import (
    TRAVEL_CEILING_CELLS_PER_SECOND,
    TRAVEL_FLOOR_CELLS_PER_SECOND,
    TRAVEL_FULL_PACE_OVERSHOOT_CELLS,
    DragTravel,
)

FIRST_EDGE = 100.0
CELL_EXTENT = 20.0
CELL_COUNT = 60
SCROLL_MAX = 800.0
FRAME = 1.0 / 60.0
BAND = TravelBand(first_edge=FIRST_EDGE, cell_extent=CELL_EXTENT, cell_count=CELL_COUNT)
BAND_NEAR = FIRST_EDGE
BAND_FAR = FIRST_EDGE + CELL_COUNT * CELL_EXTENT - SCROLL_MAX


class FakeAxis:
    """An axis that stands wherever the test puts it, and records every offset issued to it."""

    def __init__(self, *, pointer: float, scroll: float = 0.0, scroll_max: float = SCROLL_MAX) -> None:
        self._pointer = pointer
        self._scroll = scroll
        self._scroll_max = scroll_max
        self.issued: List[float] = []

    def pointer(self) -> float:
        return self._pointer

    def scroll(self) -> float:
        return self._scroll

    def scroll_max(self) -> float:
        return self._scroll_max

    def set_scroll(self, offset: float) -> None:
        self.issued.append(offset)

    def stand_at(self, pointer: float) -> None:
        self._pointer = pointer


def _travel(
    axis: FakeAxis,
    band: Optional[TravelBand] = BAND,
    frame: float = FRAME,
) -> DragTravel:
    return DragTravel(axis=axis, band=lambda: band, elapsed=lambda: frame)


def _grid(
    pointer: float,
    scroll: float = 0.0,
    frame: float = FRAME,
) -> Tuple[FakeAxis, DragTravel]:
    """A grid drawn at ``scroll``: its first cell stands that far back, so the band holds still."""
    axis = FakeAxis(pointer=pointer, scroll=scroll)
    band = TravelBand(
        first_edge=FIRST_EDGE - scroll,
        cell_extent=CELL_EXTENT,
        cell_count=CELL_COUNT,
    )
    return axis, _travel(axis, band=band, frame=frame)


class TestPointerWithinTheBand:
    """A pointer standing on the grid leaves it where it is."""

    def test_a_pointer_in_the_middle_travels_nowhere(self) -> None:
        axis = FakeAxis(pointer=(BAND_NEAR + BAND_FAR) / 2)

        _travel(axis).advance()

        assert axis.issued == []

    def test_a_pointer_on_either_edge_travels_nowhere(self) -> None:
        for pointer in (BAND_NEAR, BAND_FAR):
            axis = FakeAxis(pointer=pointer)

            _travel(axis).advance()

            assert axis.issued == []

    def test_a_grid_awaiting_its_layout_travels_nowhere(self) -> None:
        axis = FakeAxis(pointer=BAND_FAR + 500.0)

        _travel(axis, band=None).advance()

        assert axis.issued == []

    def test_a_grid_that_fits_on_screen_travels_nowhere(self) -> None:
        axis = FakeAxis(pointer=BAND_FAR + 500.0, scroll_max=0.0)

        _travel(axis).advance()

        assert axis.issued == []


class TestPace:
    """The travel answers how far past the edge the pointer is carried."""

    def test_a_pointer_just_past_the_edge_travels_at_the_floor(self) -> None:
        axis = FakeAxis(pointer=BAND_FAR + 0.5)

        _travel(axis).advance()

        assert axis.issued == [pytest.approx(TRAVEL_FLOOR_CELLS_PER_SECOND * CELL_EXTENT * FRAME, abs=0.5)]

    def test_a_pointer_carried_further_travels_faster(self) -> None:
        near_edge = FakeAxis(pointer=BAND_FAR + CELL_EXTENT)
        far_out = FakeAxis(pointer=BAND_FAR + 3 * CELL_EXTENT)

        _travel(near_edge).advance()
        _travel(far_out).advance()

        assert far_out.issued[0] > near_edge.issued[0]

    def test_the_pace_stops_rising_at_the_ceiling(self) -> None:
        at_full_pace = FakeAxis(pointer=BAND_FAR + TRAVEL_FULL_PACE_OVERSHOOT_CELLS * CELL_EXTENT)
        far_beyond = FakeAxis(pointer=BAND_FAR + 100 * CELL_EXTENT)

        _travel(at_full_pace).advance()
        _travel(far_beyond).advance()

        ceiling = TRAVEL_CEILING_CELLS_PER_SECOND * CELL_EXTENT * FRAME
        assert at_full_pace.issued == [pytest.approx(ceiling)]
        assert far_beyond.issued == [pytest.approx(ceiling)]

    def test_the_same_stretch_passes_however_fast_the_frames_arrive(self) -> None:
        """Two frames of half the duration carry the grid exactly as far as one full one."""
        whole = FakeAxis(pointer=BAND_FAR + 200.0)
        halves = FakeAxis(pointer=BAND_FAR + 200.0)

        _travel(whole).advance()
        paced = _travel(halves, frame=FRAME / 2)
        paced.advance()
        paced.advance()

        assert halves.issued[-1] == pytest.approx(whole.issued[-1])


class TestDirection:
    """The travel carries the grid toward whichever edge the pointer stands past."""

    def test_a_pointer_before_the_near_edge_travels_back(self) -> None:
        axis, travel = _grid(pointer=BAND_NEAR - 100.0, scroll=400.0)

        travel.advance()

        assert axis.issued[0] < 400.0

    def test_a_pointer_past_the_far_edge_travels_on(self) -> None:
        axis, travel = _grid(pointer=BAND_FAR + 100.0, scroll=400.0)

        travel.advance()

        assert axis.issued[0] > 400.0

    def test_the_band_travels_with_the_scroll(self) -> None:
        """A scrolled grid draws its first cell further back, so the band stands where it always did."""
        axis = FakeAxis(pointer=BAND_NEAR + 10.0, scroll=300.0)
        scrolled = TravelBand(
            first_edge=FIRST_EDGE - 300.0,
            cell_extent=CELL_EXTENT,
            cell_count=CELL_COUNT,
        )

        _travel(axis, band=scrolled).advance()

        assert axis.issued == []


class TestEnds:
    """The travel stops where the grid does."""

    def test_the_far_end_stops_at_the_scroll_extent(self) -> None:
        axis, travel = _grid(pointer=BAND_FAR + 500.0, scroll=SCROLL_MAX - 1.0)

        travel.advance()

        assert axis.issued == [SCROLL_MAX]

    def test_the_near_end_stops_at_the_start(self) -> None:
        axis, travel = _grid(pointer=BAND_NEAR - 500.0, scroll=1.0)

        travel.advance()

        assert axis.issued == [0.0]


class TestRunningOffset:
    """Each step is added to the offset last issued, since a table reports the one it was drawn with."""

    def test_travel_accumulates_while_the_grid_reports_the_offset_it_was_drawn_with(self) -> None:
        axis = FakeAxis(pointer=BAND_FAR + 500.0)
        travel = _travel(axis)

        travel.advance()
        travel.advance()
        travel.advance()

        step = axis.issued[0]
        assert axis.issued == [
            pytest.approx(step),
            pytest.approx(2 * step),
            pytest.approx(3 * step),
        ]

    def test_a_pointer_returning_to_the_band_ends_the_travel(self) -> None:
        axis = FakeAxis(pointer=BAND_FAR + 500.0)
        travel = _travel(axis)

        travel.advance()
        axis.stand_at(BAND_NEAR + 10.0)
        travel.advance()

        assert len(axis.issued) == 1

    def test_a_travel_at_rest_sets_out_from_the_offset_the_grid_is_drawn_with(self) -> None:
        axis, travel = _grid(pointer=BAND_FAR + 500.0, scroll=250.0)

        travel.advance()
        travel.rest()
        travel.advance()

        assert axis.issued[0] == pytest.approx(axis.issued[1])
