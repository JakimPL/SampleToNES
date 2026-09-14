from typing import Final, Iterator, List

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.tags.general import TAG_GLOBAL_CONTEXT_WINDOW
from sampletones_application.ui.elements.context_menu import context_menu

GESTURES: Final[int] = 5


@pytest.fixture
def dpg_context() -> Iterator[None]:
    dpg.create_context()
    try:
        yield
    finally:
        dpg.destroy_context()


def _popups() -> List[int]:
    return [window for window in dpg.get_windows() if dpg.get_item_configuration(window)["popup"]]


class TestTheApplicationHoldsOneContextMenu:
    """A dismissed menu leaves nothing behind, since the next one takes its place."""

    def test_menus_raised_in_turn_leave_one_popup_standing(self, dpg_context: None) -> None:
        for gesture in range(GESTURES):
            with context_menu():
                dpg.add_menu_item(label=f"item {gesture}")

        assert len(_popups()) == 1

    def test_the_popup_standing_holds_the_latest_menu(self, dpg_context: None) -> None:
        with context_menu():
            dpg.add_menu_item(label="earlier")

        with context_menu():
            dpg.add_menu_item(label="latest")

        items = dpg.get_item_children(TAG_GLOBAL_CONTEXT_WINDOW, 1)
        assert [dpg.get_item_label(item) for item in items] == ["latest"]
