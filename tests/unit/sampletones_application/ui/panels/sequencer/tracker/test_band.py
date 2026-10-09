from dataclasses import dataclass
from typing import Final

import pytest

from sampletones_application.ui.panels.sequencer.columns import HEADER_TABLE_ROW, HEADER_TABLE_ROWS
from sampletones_application.ui.panels.sequencer.tracker.band import TrackerBand, TrackerRows
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

ROW_HEIGHT: Final[float] = 29.0
REACH: Final[int] = 3
FRAME_ROWS: Final[int] = 8


class TestWhereTheTableRowsStand:
    """The header heads the table, the rows before the frame follow, then the frame's own, then those after."""

    def test_the_frame_starts_below_the_header_and_the_rows_before_it(self) -> None:
        rows = TrackerRows(reach=REACH, frame_rows=FRAME_ROWS)

        assert rows.table_row(0) == HEADER_TABLE_ROWS + REACH
        assert rows.body_row(0) == REACH

    def test_no_row_lands_on_the_header(self) -> None:
        rows = TrackerRows(reach=REACH, frame_rows=FRAME_ROWS)
        mapped = (
            {rows.lead_table_row(slot) for slot in range(REACH)}
            | {rows.table_row(row) for row in range(FRAME_ROWS)}
            | {rows.trail_table_row(slot) for slot in range(REACH)}
        )

        assert HEADER_TABLE_ROW not in mapped

    def test_every_row_takes_a_table_row_of_its_own_in_order(self) -> None:
        rows = TrackerRows(reach=REACH, frame_rows=FRAME_ROWS)
        mapped = (
            [rows.lead_table_row(slot) for slot in range(REACH)]
            + [rows.table_row(row) for row in range(FRAME_ROWS)]
            + [rows.trail_table_row(slot) for slot in range(REACH)]
        )

        assert mapped == list(range(HEADER_TABLE_ROWS, HEADER_TABLE_ROWS + rows.body_rows))

    def test_without_a_reach_a_pattern_row_sits_one_past_the_header(self) -> None:
        rows = TrackerRows(reach=0, frame_rows=FRAME_ROWS)

        assert [rows.table_row(row) for row in range(FRAME_ROWS)] == list(range(1, FRAME_ROWS + 1))


class TestTheBandsReach(BaseTestSuite):
    """The band reaches as many rows either side of a frame as stand above its center row."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        rows_tall: float
        expected: int

    test_cases = (
        TestCase(label="an odd number of rows, centered exactly", rows_tall=7.0, expected=3),
        TestCase(label="an even number of rows", rows_tall=8.0, expected=4),
        TestCase(label="a part of a row past an odd fit", rows_tall=7.4, expected=4),
        TestCase(label="a single row", rows_tall=1.0, expected=0),
        TestCase(label="less than one row", rows_tall=0.5, expected=0),
        TestCase(label="nothing measured", rows_tall=0.0, expected=0),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_reach(self, test_case: TestCase) -> None:
        band = TrackerBand(height=test_case.rows_tall * ROW_HEIGHT, row_height=ROW_HEIGHT)

        assert band.reach == test_case.expected


class TestCenteringARow:
    """The scroll that centers a row puts the middle of that row on the middle of the band."""

    @pytest.mark.parametrize("rows_tall", [7.0, 8.0, 7.4, 12.6])
    @pytest.mark.parametrize("frame_row", [0, 1, FRAME_ROWS - 1])
    def test_the_row_stands_at_the_center(self, rows_tall: float, frame_row: int) -> None:
        band = TrackerBand(height=rows_tall * ROW_HEIGHT, row_height=ROW_HEIGHT)
        rows = TrackerRows(reach=band.reach, frame_rows=FRAME_ROWS)

        scroll = band.centering(rows.body_row(frame_row))
        middle_on_screen = rows.body_row(frame_row) * ROW_HEIGHT - scroll + ROW_HEIGHT / 2

        assert middle_on_screen == pytest.approx(band.height / 2)

    def test_the_room_either_side_lets_every_frame_row_reach_the_center(self) -> None:
        band = TrackerBand(height=7.4 * ROW_HEIGHT, row_height=ROW_HEIGHT)
        rows = TrackerRows(reach=band.reach, frame_rows=FRAME_ROWS)
        scroll_max = rows.body_rows * ROW_HEIGHT - band.height

        for frame_row in range(FRAME_ROWS):
            assert 0.0 <= band.centering(rows.body_row(frame_row)) <= scroll_max

    def test_a_row_above_the_band_scrolls_no_further_than_the_top(self) -> None:
        band = TrackerBand(height=7.0 * ROW_HEIGHT, row_height=ROW_HEIGHT)

        assert band.centering(0) == 0.0
