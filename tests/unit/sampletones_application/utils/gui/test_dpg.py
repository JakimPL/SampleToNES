from typing import Iterator

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.dpg import dpg_get_item_parent, dpg_get_item_user_data

ROOT_TAG = "test_root"
CHILD_TAG = "test_child"
ROW_DATA = (3, "voice-id")


@pytest.fixture
def dpg_context() -> Iterator[None]:
    dpg.create_context()
    try:
        yield
    finally:
        dpg.destroy_context()


class TestAnAbsentItem:
    """A queued callback can remove an item underneath a lookup, which resolves to nothing."""

    def test_a_standing_item_names_the_one_holding_it(self, dpg_context: None) -> None:
        with dpg.window(tag=ROOT_TAG):
            dpg.add_text("held", tag=CHILD_TAG)

        assert dpg_get_item_parent(CHILD_TAG) is not None

    def test_an_item_that_has_gone_names_nothing(self, dpg_context: None) -> None:
        assert dpg_get_item_parent("never_built") is None

    def test_the_library_raises_the_base_class_for_an_absent_item(self, dpg_context: None) -> None:
        """What the helper's broad catch answers: there is nothing narrower to name.

        The day DearPyGui raises a type of its own is the day this test fails and the catch
        narrows to it.
        """
        with pytest.raises(Exception) as raised:
            dpg.get_item_parent("never_built")

        assert type(raised.value) is Exception  # pylint: disable=unidiomatic-typecheck


class TestTheUserDataOfAnItemAGestureNamed:
    """A held callback reads what a gesture landed on a frame late, so a row a rebuild took away reads as nothing."""

    def test_a_standing_item_answers_with_its_user_data(self, dpg_context: None) -> None:
        with dpg.window(tag=ROOT_TAG):
            dpg.add_selectable(label="row", tag=CHILD_TAG, user_data=ROW_DATA)

        assert dpg_get_item_user_data(CHILD_TAG) == ROW_DATA

    def test_an_item_a_rebuild_took_away_answers_with_nothing(self, dpg_context: None) -> None:
        with dpg.window(tag=ROOT_TAG):
            row = dpg.add_selectable(label="row", user_data=ROW_DATA)
        dpg.delete_item(row)

        assert dpg_get_item_user_data(row) is None

    def test_the_library_raises_for_an_item_a_rebuild_took_away(self, dpg_context: None) -> None:
        """What the guard answers: the bare read of a deleted item raises, and the callback logs it."""
        with dpg.window(tag=ROOT_TAG):
            row = dpg.add_selectable(label="row", user_data=ROW_DATA)
        dpg.delete_item(row)

        with pytest.raises(Exception, match="Item not found"):
            dpg.get_item_user_data(row)
