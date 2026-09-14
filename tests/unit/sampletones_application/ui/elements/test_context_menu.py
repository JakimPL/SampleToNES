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

    def test_a_dismissed_popup_opens_again_for_the_next_menu(self, dpg_context: None) -> None:
        with context_menu():
            dpg.add_menu_item(label="earlier")
        dpg.configure_item(TAG_GLOBAL_CONTEXT_WINDOW, show=False)

        with context_menu():
            dpg.add_menu_item(label="latest")

        assert dpg.get_item_configuration(TAG_GLOBAL_CONTEXT_WINDOW)["show"] is True

    def test_a_menu_takes_the_place_of_one_still_open(self, dpg_context: None) -> None:
        """A menu raised over one still standing builds into the popup already shown."""
        with context_menu():
            dpg.add_menu_item(label="earlier")
        standing = dpg.get_alias_id(TAG_GLOBAL_CONTEXT_WINDOW)

        with context_menu():
            dpg.add_menu_item(label="latest")

        assert (dpg.get_alias_id(TAG_GLOBAL_CONTEXT_WINDOW), dpg.get_item_configuration(standing)["show"]) == (
            standing,
            True,
        )
