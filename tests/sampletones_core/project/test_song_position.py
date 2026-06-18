from dataclasses import dataclass

import pytest

from sampletones_core.project.song_position import SongPosition
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase


def _advance(order_position: int, row_index: int, *, rows: int, length: int) -> SongPosition:
    position = SongPosition(order_position=order_position, row_index=row_index)
    position.advance(rows_in_pattern=rows, order_length=length)
    return position


class TestSongPositionConstruction:
    def test_negative_order_position_raises(self) -> None:
        with pytest.raises(ValueError, match="order_position"):
            SongPosition(order_position=-1)

    def test_negative_row_index_raises(self) -> None:
        with pytest.raises(ValueError, match="row_index"):
            SongPosition(row_index=-1)

    def test_both_zero_is_valid(self) -> None:
        position = SongPosition()
        assert position.order_position == 0
        assert position.row_index == 0


class TestAdvanceSingleStep(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        start_order: int
        start_row: int
        rows: int
        length: int
        expected_order: int
        expected_row: int

        @property
        def label(self) -> str:
            return str(self.expected)

    test_cases = [
        TestCase(
            expected="mid_pattern_increments_row",
            start_order=0,
            start_row=2,
            rows=4,
            length=3,
            expected_order=0,
            expected_row=3,
        ),
        TestCase(
            expected="last_row_wraps_to_next_frame",
            start_order=0,
            start_row=3,
            rows=4,
            length=3,
            expected_order=1,
            expected_row=0,
        ),
        TestCase(
            expected="last_frame_last_row_reaches_end_sentinel",
            start_order=2,
            start_row=3,
            rows=4,
            length=3,
            expected_order=3,
            expected_row=0,
        ),
        TestCase(
            expected="single_row_pattern_wraps_immediately",
            start_order=0,
            start_row=0,
            rows=1,
            length=3,
            expected_order=1,
            expected_row=0,
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_advance(self, test_case: TestCase) -> None:
        result = _advance(
            test_case.start_order,
            test_case.start_row,
            rows=test_case.rows,
            length=test_case.length,
        )
        assert result.order_position == test_case.expected_order
        assert result.row_index == test_case.expected_row


class TestAdvanceSequence:
    def test_full_pattern_traversal_lands_on_next_frame(self) -> None:
        rows = 4
        position = SongPosition()

        for _ in range(rows):
            position.advance(rows_in_pattern=rows, order_length=2)

        assert position.order_position == 1
        assert position.row_index == 0

    def test_finished_position_is_stable_under_repeated_advance(self) -> None:
        position = SongPosition(order_position=0, row_index=3)
        position.advance(rows_in_pattern=4, order_length=1)

        assert position.order_position == 1

        position.advance(rows_in_pattern=4, order_length=1)
        position.advance(rows_in_pattern=4, order_length=1)

        assert position.order_position == 1
        assert position.row_index == 0


class TestSongPositionIteration:
    def test_unpacks_as_order_then_row(self) -> None:
        order_position, row_index = SongPosition(order_position=3, row_index=7)
        assert order_position == 3
        assert row_index == 7
