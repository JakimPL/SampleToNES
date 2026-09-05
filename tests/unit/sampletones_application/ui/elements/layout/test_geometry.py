from dataclasses import dataclass

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
REGION_HEIGHT = 100.0
TRAVEL = 1000.0


def measured(*, overscan: int = OVERSCAN, pitch: float = PITCH) -> RowGeometry:
    """A reading of the room one row takes, as a region that has drawn rows would hold it."""
    return RowGeometry(overscan=overscan, pitch=pitch)


class TestAnUnmeasuredGeometry(BaseTestSuite):
    """A geometry that has yet to read a row works from the least room a row can take, so a first
    draw is generous rather than unbounded."""

    def test_it_reports_no_reading(self) -> None:
        assert not RowGeometry.unmeasured(overscan=OVERSCAN).measured

    def test_it_works_from_the_floor(self) -> None:
        assert RowGeometry.unmeasured(overscan=OVERSCAN).room == MINIMUM_ROW_PITCH

    def test_its_window_is_wider_than_a_measured_one(self) -> None:
        """A floor no row goes under makes the first window larger than it needs to be, never
        smaller, so the rows the region shows are among the ones it built."""
        unmeasured = RowGeometry.unmeasured(overscan=OVERSCAN)
        assert unmeasured.size(REGION_HEIGHT) > measured().size(REGION_HEIGHT)

    def test_it_still_holds_a_long_list_back(self) -> None:
        assert RowGeometry.unmeasured(overscan=OVERSCAN).windows(height=REGION_HEIGHT, total=10_000)

    def test_a_short_list_is_drawn_whole(self) -> None:
        geometry = RowGeometry.unmeasured(overscan=OVERSCAN)
        assert geometry.slice_of(offset=0.0, extent=0.0, height=REGION_HEIGHT, total=3) == (0, 3)


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
    """Where a window opens follows how far through its travel the region is scrolled, so the top
    of the list is reachable at the top and the end of it at the end."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        offset: float
        total: int
        expected: Window

    test_cases = (
        TestCase(label="a_short_list_is_drawn_whole", offset=0.0, total=8, expected=(0, 8)),
        TestCase(label="a_list_the_size_of_the_window_is_drawn_whole", offset=0.0, total=10, expected=(0, 10)),
        TestCase(label="the_top_opens_at_the_first_row", offset=0.0, total=100, expected=(0, 10)),
        TestCase(label="the_middle_opens_halfway_down", offset=TRAVEL / 2, total=100, expected=(45, 10)),
        TestCase(label="the_end_opens_at_the_last_rows", offset=TRAVEL, total=100, expected=(90, 10)),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_slice_follows_the_travel(self, test_case: TestCase) -> None:
        window = measured().slice_of(
            offset=test_case.offset,
            extent=TRAVEL,
            height=REGION_HEIGHT,
            total=test_case.total,
        )
        assert window == test_case.expected

    def test_the_end_of_the_list_is_reachable(self) -> None:
        """A region scrolled to the end of its travel builds the rows at the end of its list."""
        total = 5_000
        geometry = measured()
        start, count = geometry.slice_of(offset=TRAVEL, extent=TRAVEL, height=REGION_HEIGHT, total=total)
        assert start + count == total

    def test_a_region_with_no_travel_opens_at_the_top(self) -> None:
        """A region measured before it has been laid out reports no travel, and the top of a list
        is what stands until it reports some."""
        geometry = measured()
        start, _ = geometry.slice_of(offset=500.0, extent=0.0, height=REGION_HEIGHT, total=100)
        assert start == 0

    @pytest.mark.parametrize("offset", range(0, 1001, 37))
    def test_a_window_stays_inside_the_list_at_any_offset(self, offset: int) -> None:
        total = 100
        start, count = measured().slice_of(
            offset=float(offset),
            extent=TRAVEL,
            height=REGION_HEIGHT,
            total=total,
        )
        assert start >= 0
        assert start + count <= total

    def test_the_window_only_moves_forward_as_the_region_scrolls(self) -> None:
        geometry = measured()
        previous = 0
        for offset in range(0, 1001, 13):
            start, _ = geometry.slice_of(offset=float(offset), extent=TRAVEL, height=REGION_HEIGHT, total=500)
            assert start >= previous
            previous = start


class TestReserve(BaseTestSuite):
    """The rows a window passed over stand as the room they would have taken, which is what keeps
    the scrollbar proportional to the whole list."""

    @pytest.mark.parametrize("rows", (0, 1, 7, 5_000))
    def test_reserve_is_the_room_those_rows_take(self, rows: int) -> None:
        assert measured().reserve(rows) == int(rows * PITCH)

    def test_an_unmeasured_geometry_reserves_by_the_floor(self) -> None:
        rows = 100
        geometry = RowGeometry.unmeasured(overscan=OVERSCAN)
        assert geometry.reserve(rows) == int(rows * MINIMUM_ROW_PITCH)

    def test_the_reserves_and_the_drawn_rows_span_the_list(self) -> None:
        geometry = measured()
        total = 100
        start, count = geometry.slice_of(offset=400.0, extent=TRAVEL, height=REGION_HEIGHT, total=total)
        spanned = geometry.reserve(start) + geometry.reserve(count) + geometry.reserve(total - start - count)
        assert spanned == geometry.reserve(total)


class TestTake(BaseTestSuite):
    """A reading is taken from the block of rows a region drew, so whatever a table lays around
    its rows is carried by the same number that reserves room for them."""

    def test_a_reading_gives_the_room_one_row_takes(self) -> None:
        geometry = RowGeometry.unmeasured(overscan=OVERSCAN)
        geometry.take(block=200.0, rows=10)
        assert geometry.pitch == pytest.approx(20.0)
        assert geometry.measured

    def test_a_first_reading_is_worth_redrawing(self) -> None:
        geometry = RowGeometry.unmeasured(overscan=OVERSCAN)
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
