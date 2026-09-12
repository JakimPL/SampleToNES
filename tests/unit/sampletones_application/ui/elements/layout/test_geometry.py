from dataclasses import dataclass
from typing import Tuple

import pytest

from sampletones_application.ui.elements.layout.geometry import (
    GEOMETRY_TOLERANCE,
    MINIMUM_ROW_PITCH,
    RowGeometry,
    Window,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

OVERSCAN = 2
PITCH = 20.0
OPENING = 16.0
REGION_HEIGHT = 100.0
TOTAL_ROWS = 100
READING_STEPS = 40


def measured(*, overscan: int = OVERSCAN, pitch: float = PITCH) -> RowGeometry:
    """A reading of the room one row takes, as a region that has drawn rows would hold it."""
    return RowGeometry(overscan=overscan, pitch=pitch, opening=OPENING)


class TestAnUnmeasuredGeometry(BaseTestSuite):
    """A geometry that has yet to read a row works from the height its layout gives one, so a
    first draw builds about the rows the region shows."""

    def test_it_reports_no_reading(self) -> None:
        assert not RowGeometry.opening_at(overscan=OVERSCAN, opening=OPENING).measured

    def test_it_works_from_the_opening_it_was_given(self) -> None:
        assert RowGeometry.opening_at(overscan=OVERSCAN, opening=OPENING).room == OPENING

    def test_an_opening_under_the_floor_is_held_to_it(self) -> None:
        """No theme draws a row that small, so a figure below the floor opens at the floor."""
        opened = RowGeometry.opening_at(overscan=OVERSCAN, opening=MINIMUM_ROW_PITCH / 2)
        assert opened.room == MINIMUM_ROW_PITCH

    def test_its_window_covers_what_a_measured_one_covers(self) -> None:
        """The opening stands close to what a row takes, so the first slice reaches the rows the
        region shows rather than several times as many."""
        unmeasured = RowGeometry.opening_at(overscan=OVERSCAN, opening=OPENING)
        assert unmeasured.size(REGION_HEIGHT) >= measured().size(REGION_HEIGHT)
        assert unmeasured.size(REGION_HEIGHT) < 2 * measured().size(REGION_HEIGHT)

    def test_it_still_holds_a_long_list_back(self) -> None:
        assert RowGeometry.opening_at(overscan=OVERSCAN, opening=OPENING).windows(height=REGION_HEIGHT, total=10_000)

    def test_a_short_list_is_drawn_whole(self) -> None:
        geometry = RowGeometry.opening_at(overscan=OVERSCAN, opening=OPENING)
        assert geometry.slice_of(offset=0.0, height=REGION_HEIGHT, total=3) == (0, 3)


class TestAMeasuredGeometry(BaseTestSuite):
    """A reading taken from drawn rows is what every room the region reserves is worked out from."""

    def test_the_room_is_the_reading(self) -> None:
        assert measured().room == PITCH

    def test_it_reports_a_reading(self) -> None:
        assert measured().measured


class TestWindowSize(BaseTestSuite):
    """The window holds the rows the region shows and an overscan beyond each edge, so a scroll
    in either direction meets rows already standing."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        height: float
        pitch: float
        overscan: int
        expected: int

    test_cases = (
        TestCase(label="five_rows_fit", height=100.0, pitch=20.0, overscan=2, expected=10),
        TestCase(label="a_partial_row_counts", height=110.0, pitch=20.0, overscan=2, expected=10),
        TestCase(label="no_overscan_shows_what_fits", height=100.0, pitch=20.0, overscan=0, expected=6),
        TestCase(label="a_region_shorter_than_a_row_holds_one", height=5.0, pitch=20.0, overscan=0, expected=1),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_size_counts_what_shows_and_the_overscan(self, test_case: TestCase) -> None:
        geometry = measured(overscan=test_case.overscan, pitch=test_case.pitch)
        assert geometry.size(test_case.height) == test_case.expected


class TestSliceOf(BaseTestSuite):
    """Where a window opens is where the offset stands counted in the rooms the region reserves
    by, so the top of the list is reachable at the top and the end of it at the end."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        offset: float
        total: int
        expected: Window

    test_cases = (
        TestCase(label="a_short_list_is_drawn_whole", offset=0.0, total=8, expected=(0, 8)),
        TestCase(label="a_list_the_size_of_the_window_is_drawn_whole", offset=0.0, total=10, expected=(0, 10)),
        TestCase(label="the_top_opens_at_the_first_row", offset=0.0, total=TOTAL_ROWS, expected=(0, 10)),
        TestCase(label="a_row_down_carries_the_overscan", offset=PITCH, total=TOTAL_ROWS, expected=(0, 10)),
        TestCase(label="the_middle_opens_halfway_down", offset=950.0, total=TOTAL_ROWS, expected=(45, 10)),
        TestCase(label="the_end_opens_at_the_last_rows", offset=1900.0, total=TOTAL_ROWS, expected=(90, 10)),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_slice_follows_the_rooms_the_offset_counts_out(self, test_case: TestCase) -> None:
        window = measured().slice_of(
            offset=test_case.offset,
            height=REGION_HEIGHT,
            total=test_case.total,
        )
        assert window == test_case.expected

    def test_a_window_holds_the_same_rows_however_long_the_list(self) -> None:
        """This is the claim a folder rests on: opening ten thousand costs what opening ten costs,
        because the rows outside the window stand as reserved room rather than as widgets."""
        geometry = measured()

        _, few = geometry.slice_of(offset=0.0, height=REGION_HEIGHT, total=TOTAL_ROWS)
        _, many = geometry.slice_of(offset=0.0, height=REGION_HEIGHT, total=100 * TOTAL_ROWS)

        assert few == many

    def test_the_end_of_the_list_is_reachable(self) -> None:
        """A region scrolled to the end of its rows builds the rows at the end of its list."""
        total = 5_000
        geometry = measured()
        start, count = geometry.slice_of(offset=total * PITCH, height=REGION_HEIGHT, total=total)
        assert start + count == total

    @pytest.mark.parametrize("offset", range(0, 2001, 37))
    def test_a_window_stays_inside_the_list_at_any_offset(self, offset: int) -> None:
        start, count = measured().slice_of(
            offset=float(offset),
            height=REGION_HEIGHT,
            total=TOTAL_ROWS,
        )
        assert start >= 0
        assert start + count <= TOTAL_ROWS

    def test_the_window_only_moves_forward_as_the_region_scrolls(self) -> None:
        geometry = measured()
        previous = 0
        for offset in range(0, 10_001, 13):
            start, _ = geometry.slice_of(offset=float(offset), height=REGION_HEIGHT, total=500)
            assert start >= previous
            previous = start


class TestTheWindowCoversTheRegion(BaseTestSuite):
    """The rows a window names stand across the region the offset it was chosen for is looking at.

    A window is placed by the room reserved above it and filled with rows of whatever height the
    theme draws them at, so the two agree in length only while the reading is exact. The rows
    have to reach across the region either way: a reading over the height a row really takes is
    what a list whose rows are drawn in tables of their own leaves behind, and a window chosen
    against it left the foot of an open folder blank and its last rows out of reach.
    """

    @pytest.mark.parametrize("drawn", (PITCH * 0.8, PITCH, PITCH * 1.3))
    def test_the_rows_it_names_reach_across_the_region(self, drawn: float) -> None:
        geometry = measured()
        for offset in self._offsets(geometry, drawn):
            start, count = geometry.slice_of(offset=offset, height=REGION_HEIGHT, total=TOTAL_ROWS)
            head = float(geometry.reserve(start))
            assert head <= offset
            assert head + count * drawn >= offset + REGION_HEIGHT

    @pytest.mark.parametrize("drawn", (PITCH * 0.8, PITCH, PITCH * 1.3))
    def test_the_last_row_stands_at_the_foot(self, drawn: float) -> None:
        geometry = measured()
        start, count = geometry.slice_of(
            offset=self._offsets(geometry, drawn)[-1],
            height=REGION_HEIGHT,
            total=TOTAL_ROWS,
        )
        assert start + count == TOTAL_ROWS

    @staticmethod
    def _offsets(geometry: RowGeometry, drawn: float) -> Tuple[float, ...]:
        """Every position the reader can scroll a region whose rows are drawn ``drawn`` tall.

        What the region holds is the two reserves and the block of drawn rows, so a row drawn at
        a height the reading overstates makes the content shorter than the rooms it was reserved
        in, and the reader stops short of the travel the reserves alone would give.
        """
        count = geometry.size(REGION_HEIGHT)
        content = geometry.reserve(TOTAL_ROWS) - geometry.reserve(count) + count * drawn
        travel = content - REGION_HEIGHT
        return tuple(travel * step / READING_STEPS for step in range(READING_STEPS + 1))


class TestReserve(BaseTestSuite):
    """The rows a window passed over stand as the room they would have taken, which is what keeps
    the scrollbar proportional to the whole list."""

    @pytest.mark.parametrize("rows", (0, 1, 7, 5_000))
    def test_reserve_is_the_room_those_rows_take(self, rows: int) -> None:
        assert measured().reserve(rows) == int(rows * PITCH)

    def test_an_unmeasured_geometry_reserves_by_its_opening(self) -> None:
        rows = 100
        geometry = RowGeometry.opening_at(overscan=OVERSCAN, opening=OPENING)
        assert geometry.reserve(rows) == int(rows * OPENING)

    def test_the_reserves_and_the_drawn_rows_span_the_list(self) -> None:
        geometry = measured()
        total = 100
        start, count = geometry.slice_of(offset=400.0, height=REGION_HEIGHT, total=total)
        spanned = geometry.reserve(start) + geometry.reserve(count) + geometry.reserve(total - start - count)
        assert spanned == geometry.reserve(total)


class TestTake(BaseTestSuite):
    """A reading is taken from the block of rows a region drew, so whatever a table lays around
    its rows is carried by the same number that reserves room for them."""

    def test_a_reading_gives_the_room_one_row_takes(self) -> None:
        geometry = RowGeometry.opening_at(overscan=OVERSCAN, opening=OPENING)
        geometry.take(block=200.0, rows=10)
        assert geometry.pitch == pytest.approx(20.0)
        assert geometry.measured

    def test_a_first_reading_is_worth_redrawing(self) -> None:
        geometry = RowGeometry.opening_at(overscan=OVERSCAN, opening=OPENING)
        assert geometry.take(block=200.0, rows=10)

    def test_a_reading_that_holds_asks_for_no_redraw(self) -> None:
        geometry = measured()
        assert not geometry.take(block=PITCH * 10, rows=10)

    def test_a_move_within_the_tolerance_asks_for_no_redraw(self) -> None:
        geometry = measured()
        drift = GEOMETRY_TOLERANCE / 2
        assert not geometry.take(block=(PITCH + drift) * 10, rows=10)

    def test_a_move_past_the_tolerance_is_worth_redrawing(self) -> None:
        geometry = measured()
        drift = GEOMETRY_TOLERANCE * 2
        assert geometry.take(block=(PITCH + drift) * 10, rows=10)

    @pytest.mark.parametrize("rows", (0, -1))
    def test_a_block_of_no_rows_leaves_the_reading_alone(self, rows: int) -> None:
        geometry = measured()
        assert not geometry.take(block=200.0, rows=rows)
        assert geometry.pitch == PITCH

    @pytest.mark.parametrize("block", (0.0, -50.0, MINIMUM_ROW_PITCH * 10 - 1))
    def test_a_block_measured_while_the_rows_were_clipped_is_let_be(self, block: float) -> None:
        """A block giving a row less than the floor is a region measured before its rows were
        placed, and taking it would put every region sharing the reading out of step."""
        geometry = measured()
        assert not geometry.take(block=block, rows=10)
        assert geometry.pitch == PITCH
