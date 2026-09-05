from typing import Iterator

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.dpg import dpg_get_item_parent

ROOT_TAG = "test_root"
CHILD_TAG = "test_child"


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
