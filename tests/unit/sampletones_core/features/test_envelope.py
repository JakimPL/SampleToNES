from dataclasses import dataclass
from typing import Final, Optional, Tuple

import pytest
from pydantic import ValidationError

from sampletones_core.features.envelope import Envelope
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

ITEM_LIMIT: Final[int] = 252


def items_of(length: int) -> Tuple[int, ...]:
    return tuple(index % 16 for index in range(length))


class TestWhatADimensionHoldsAtATick(BaseTestSuite):
    """A dimension answers at every tick, which is what lets a note sound past its written frames."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        items: Tuple[int, ...]
        loop_point: Optional[int]
        expected: Tuple[Optional[int], ...]

    test_cases = (
        TestCase(
            label="a dimension the channel governs answers nothing",
            items=(),
            loop_point=None,
            expected=(None, None, None),
        ),
        TestCase(
            label="a dimension halting holds its final value",
            items=(15, 8, 4),
            loop_point=None,
            expected=(15, 8, 4, 4, 4),
        ),
        TestCase(
            label="a dimension looping circles from its point",
            items=(15, 8, 4),
            loop_point=1,
            expected=(15, 8, 4, 8, 4, 8),
        ),
        TestCase(
            label="a dimension looping from the start circles whole",
            items=(9, 3),
            loop_point=0,
            expected=(9, 3, 9, 3, 9),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_value_at_each_tick(self, test_case: TestCase) -> None:
        envelope = Envelope[int](items=test_case.items, loop_point=test_case.loop_point)

        assert tuple(envelope.at(tick) for tick in range(len(test_case.expected))) == test_case.expected


class TestWhatADimensionStates:
    def test_a_written_dimension_takes_itself_out_of_the_channels_own(self) -> None:
        assert Envelope[int](items=(15,)).written

    def test_an_empty_dimension_is_left_to_the_channel(self) -> None:
        assert not Envelope[int]().written

    def test_a_dimension_states_whether_it_circles(self) -> None:
        assert Envelope[int](items=(15, 8), loop_point=0).loops
        assert not Envelope[int](items=(15, 8)).loops

    def test_a_point_past_the_items_written_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            Envelope[int](items=(15, 8), loop_point=2)

    def test_a_point_on_a_dimension_writing_nothing_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            Envelope[int](items=(), loop_point=0)


class TestADimensionWithinALimit:
    """``limited`` states no limit of its own: whoever asks for one is where it comes from."""

    def test_a_dimension_within_the_limit_stands_as_written(self) -> None:
        envelope = Envelope[int](items=(15, 12, 9, 0))

        assert envelope.limited(ITEM_LIMIT) == envelope

    def test_an_over_long_dimension_keeps_its_opening_items(self) -> None:
        limited = Envelope[int](items=items_of(ITEM_LIMIT + 48)).limited(ITEM_LIMIT)

        assert limited.items == items_of(ITEM_LIMIT)

    def test_a_point_past_what_survives_moves_to_the_last_item_kept(self) -> None:
        limited = Envelope[int](items=items_of(ITEM_LIMIT + 48), loop_point=ITEM_LIMIT + 10).limited(ITEM_LIMIT)

        assert limited.loop_point == ITEM_LIMIT - 1

    def test_a_point_inside_what_survives_stays_where_it_was(self) -> None:
        limited = Envelope[int](items=items_of(ITEM_LIMIT + 48), loop_point=4).limited(ITEM_LIMIT)

        assert limited.loop_point == 4


class TestADimensionBroughtToALength:
    def test_a_shorter_dimension_holds_its_final_value(self) -> None:
        assert Envelope[int](items=(0, 2, 4)).resized(5).items == (0, 2, 4, 4, 4)

    def test_a_dimension_at_the_length_stands_as_written(self) -> None:
        envelope = Envelope[int](items=(15, 12, 9))

        assert envelope.resized(3) == envelope

    def test_a_dimension_the_channel_governs_stays_empty(self) -> None:
        assert Envelope[int]().resized(5).items == ()

    def test_a_point_stays_inside_the_items_kept(self) -> None:
        resized = Envelope[int](items=(15, 12, 9, 0), loop_point=3).resized(2)

        assert resized.items == (15, 12)
        assert resized.loop_point == 1
