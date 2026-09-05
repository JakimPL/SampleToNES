from dataclasses import dataclass

import pytest

from sampletones_application.ui.elements.layout.geometry import (
    GEOMETRY_TOLERANCE,
    RowGeometry,
    Window,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

OVERSCAN = 2
PITCH = 20.0
REGION_HEIGHT = 100.0


def measured(*, overscan: int = OVERSCAN, pitch: float = PITCH) -> RowGeometry:
    """A reading of the room one row takes, as a region that has drawn rows would hold it."""
    return RowGeometry(overscan=overscan, pitch=pitch)


class TestUnmeasuredGeometry(BaseTestSuite):
    """A geometry that has yet to read a row holds the whole list in its window, so the region
    draws everything and the next frame has something to measure."""

    def test_it_reports_no_reading(self) -> None:
        assert not RowGeometry.unmeasured(overscan=OVERSCAN).measured

    @pytest.mark.parametrize("total", (0, 1, 10, 10_000))
    def test_it_windows_no_list(self, total: int) -> None:
        geometry = RowGeometry.unmeasured(overscan=OVERSCAN)
        assert not geometry.windows(height=REGION_HEIGHT, total=total)

    @pytest.mark.parametrize("total", (0, 1, 10, 10_000))
    def test_its_slice_is_the_whole_list(self, total: int) -> None:
        geometry = RowGeometry.unmeasured(overscan=OVERSCAN)
        assert geometry.slice_of(offset=0.0, height=REGION_HEIGHT, total=total) == (0, total)

    def test_it_reserves_nothing(self) -> None:
        assert RowGeometry.unmeasured(overscan=OVERSCAN).reserve(100) == 0


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
    """Where a window opens follows the scroll position, held inside the list it slices."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        offset: float
        total: int
        expected: Window

    test_cases = (
        TestCase(label="a_short_list_is_drawn_whole", offset=0.0, total=8, expected=(0, 8)),
        TestCase(label="a_list_the_size_of_the_window_is_drawn_whole", offset=0.0, total=10, expected=(0, 10)),
        TestCase(label="the_top_opens_at_the_first_row", offset=0.0, total=100, expected=(0, 10)),
        TestCase(label="a_scroll_carries_the_overscan_above_it", offset=200.0, total=100, expected=(8, 10)),
        TestCase(label="the_bottom_holds_the_window_inside_the_list", offset=2000.0, total=100, expected=(90, 10)),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_slice_follows_the_offset(self, test_case: TestCase) -> None:
        geometry = measured()
        window = geometry.slice_of(offset=test_case.offset, height=REGION_HEIGHT, total=test_case.total)
        assert window == test_case.expected

    @pytest.mark.parametrize("offset", range(0, 2400, 37))
    def test_a_window_stays_inside_the_list_at_any_offset(self, offset: int) -> None:
        total = 100
        geometry = measured()
        start, count = geometry.slice_of(offset=float(offset), height=REGION_HEIGHT, total=total)
        assert start >= 0
        assert start + count <= total

    def test_a_scrolled_window_covers_the_row_the_offset_reaches(self) -> None:
        """The row a reader has scrolled to stands among the ones the window built."""
        total = 100
        geometry = measured()
        for offset in range(0, int(total * PITCH), 17):
            start, count = geometry.slice_of(offset=float(offset), height=REGION_HEIGHT, total=total)
            reached = min(int(offset / PITCH), total - 1)
            assert start <= reached < start + count


class TestReserve(BaseTestSuite):
    """The rows a window passed over stand as the room they would have taken, which is what keeps
    the scrollbar proportional to the whole list."""

    @pytest.mark.parametrize("rows", (0, 1, 7, 5_000))
    def test_reserve_is_the_room_those_rows_take(self, rows: int) -> None:
        assert measured().reserve(rows) == int(rows * PITCH)

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

    @pytest.mark.parametrize(
        ("block", "rows"),
        ((200.0, 0), (200.0, -1), (0.0, 10), (-50.0, 10)),
    )
    def test_a_block_with_nothing_to_read_leaves_the_reading_alone(self, block: float, rows: int) -> None:
        geometry = measured()
        assert not geometry.take(block=block, rows=rows)
        assert geometry.pitch == PITCH
