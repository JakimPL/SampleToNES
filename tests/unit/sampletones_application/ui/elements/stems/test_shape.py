from dataclasses import dataclass
from typing import Tuple

import pytest

from sampletones_application.ui.elements.stems.shape import ListShape, Reshape, RowPlacement
from sampletones_core.constants.enums import ChannelName
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

CHANNELS: Tuple[ChannelName, ...] = (ChannelName.PULSE1, ChannelName.TRIANGLE)


def placed(
    key: str,
    *,
    level: int = 0,
    opened: bool = False,
    held: Tuple[str, ...] = (),
    offered: Tuple[ChannelName, ...] = CHANNELS,
) -> RowPlacement:
    """One row as a shape records it."""
    return RowPlacement(
        key=key,
        level=level,
        offered=frozenset(offered),
        opened=opened,
        held=held,
    )


def shaped(*rows: RowPlacement, columns: Tuple[ChannelName, ...] = CHANNELS, collapsed: bool = True) -> ListShape:
    """The shape a list of these rows amounts to."""
    return ListShape(columns=columns, collapsed=collapsed, rows=rows)


class TestWhatAReadingAsksFor(BaseTestSuite):
    """A shape says whether the widgets standing can be brought to a new reading, and how far.

    The whole list is drawn again where the tables are built around what changed — the columns,
    the banding, which rows stand and where. A recording leaving the folder it was gathered under
    reaches that folder's own region alone, which is what lets the rows around it keep the widgets
    they stand as and the reader keep the scroll they left.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        standing: ListShape
        incoming: ListShape
        expected: Reshape

    test_cases = (
        TestCase(
            label="the_same_shape_asks_for_nothing",
            standing=shaped(placed("bass"), placed("drums", held=("one", "two"))),
            incoming=shaped(placed("bass"), placed("drums", held=("one", "two"))),
            expected=Reshape.within(()),
        ),
        TestCase(
            label="a_recording_leaving_a_folder_reaches_that_folder",
            standing=shaped(placed("bass"), placed("drums", held=("one", "two"))),
            incoming=shaped(placed("bass"), placed("drums", held=("one",))),
            expected=Reshape.within(("drums",)),
        ),
        TestCase(
            label="two_folders_changing_at_once_name_them_both",
            standing=shaped(placed("drums", held=("one", "two")), placed("keys", held=("three", "four"))),
            incoming=shaped(placed("drums", held=("one",)), placed("keys", held=("three",))),
            expected=Reshape.within(("drums", "keys")),
        ),
        TestCase(
            label="a_row_arriving_reaches_the_whole_list",
            standing=shaped(placed("bass")),
            incoming=shaped(placed("bass"), placed("lead")),
            expected=Reshape.everything(),
        ),
        TestCase(
            label="a_row_leaving_reaches_the_whole_list",
            standing=shaped(placed("bass"), placed("lead")),
            incoming=shaped(placed("bass")),
            expected=Reshape.everything(),
        ),
        TestCase(
            label="a_folder_opening_reaches_the_whole_list",
            standing=shaped(placed("drums", held=("one",))),
            incoming=shaped(placed("drums", opened=True, held=("one",))),
            expected=Reshape.everything(),
        ),
        TestCase(
            label="a_row_changing_band_reaches_the_whole_list",
            standing=shaped(placed("bass", level=0)),
            incoming=shaped(placed("bass", level=1)),
            expected=Reshape.everything(),
        ),
        TestCase(
            label="a_row_offering_another_channel_reaches_the_whole_list",
            standing=shaped(placed("bass", offered=(ChannelName.PULSE1,))),
            incoming=shaped(placed("bass", offered=CHANNELS)),
            expected=Reshape.everything(),
        ),
        TestCase(
            label="a_column_arriving_reaches_the_whole_list",
            standing=shaped(placed("bass"), columns=(ChannelName.PULSE1,)),
            incoming=shaped(placed("bass"), columns=CHANNELS),
            expected=Reshape.everything(),
        ),
        TestCase(
            label="the_banding_changing_reaches_the_whole_list",
            standing=shaped(placed("bass"), collapsed=True),
            incoming=shaped(placed("bass"), collapsed=False),
            expected=Reshape.everything(),
        ),
        TestCase(
            label="a_row_that_both_moves_and_loses_a_recording_reaches_the_whole_list",
            standing=shaped(placed("drums", level=0, held=("one", "two"))),
            incoming=shaped(placed("drums", level=1, held=("one",))),
            expected=Reshape.everything(),
        ),
        TestCase(
            label="a_row_taking_another_rows_place_reaches_the_whole_list",
            standing=shaped(placed("bass"), placed("lead")),
            incoming=shaped(placed("lead"), placed("bass")),
            expected=Reshape.everything(),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_what_the_incoming_shape_asks_of_the_standing_one(self, test_case: TestCase) -> None:
        assert test_case.incoming.against(test_case.standing) == test_case.expected


class TestWhetherAnythingIsDrawn(BaseTestSuite):
    """Whoever answers a reshape settles the regions once widgets have been built."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        reshape: Reshape

    test_cases = (
        TestCase(label="nothing_draws_nothing", reshape=Reshape.nothing(), expected=False),
        TestCase(label="the_whole_list_draws", reshape=Reshape.everything(), expected=True),
        TestCase(label="one_folder_draws", reshape=Reshape.within(("drums",)), expected=True),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_whether_widgets_were_built(self, test_case: TestCase) -> None:
        assert test_case.reshape.redraws is test_case.expected

    def test_a_reshape_naming_no_folder_is_the_one_that_asks_for_nothing(self) -> None:
        """Both stand for a reading the standing widgets already show, so they are one reshape."""
        assert Reshape.within(()) == Reshape.nothing()


class TestWhereARowStands(BaseTestSuite):
    """A placement answers whether two readings put the same row in the same place.

    What a folder holds is answered separately, so it plays no part in where the folder's own
    row stands; the band it sits in and whether it stands open both do.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        standing: RowPlacement
        incoming: RowPlacement

    test_cases = (
        TestCase(
            label="what_a_folder_holds_leaves_it_where_it_was",
            standing=placed("drums", held=("one",)),
            incoming=placed("drums", held=("one", "two")),
            expected=True,
        ),
        TestCase(
            label="a_row_that_moved_band_stands_elsewhere",
            standing=placed("drums", level=1),
            incoming=placed("drums", level=0),
            expected=False,
        ),
        TestCase(
            label="a_folder_that_opened_stands_elsewhere",
            standing=placed("drums"),
            incoming=placed("drums", opened=True),
            expected=False,
        ),
        TestCase(
            label="a_row_offered_other_channels_stands_elsewhere",
            standing=placed("drums", offered=(ChannelName.PULSE1,)),
            incoming=placed("drums", offered=CHANNELS),
            expected=False,
        ),
        TestCase(
            label="another_row_stands_elsewhere",
            standing=placed("drums"),
            incoming=placed("bass"),
            expected=False,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_whether_two_readings_stand_the_row_the_same_way(self, test_case: TestCase) -> None:
        assert test_case.incoming.stands_where(test_case.standing) is test_case.expected
