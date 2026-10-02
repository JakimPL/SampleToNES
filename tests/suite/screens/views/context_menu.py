from typing import Final, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import TAG_GLOBAL_CONTEXT_WINDOW, TAG_GLOBAL_TAB_INSTRUCTIONS
from sampletones_application.utils.callbacks.queue import CallbackQueue
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.geometry import Point, Rect
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items import (
    MENU_ITEM_TYPE,
    MENU_TYPE,
    EntryReading,
    Item,
    find_labelled,
    read_item,
    read_label,
    read_popup_entries,
)
from tests.suite.screens.dearpygui.semantic import invoke

ENTRY_INSET: Final[Point] = Point(x=12, y=8)
CLEAR_OF_THE_TABS: Final[int] = 48
ENABLED: Final[str] = "enabled"
OPENING_FRAMES: Final[int] = 3


class MissingEntryError(AssertionError):
    """Raised when a scenario chooses an entry the open menu does not offer."""


class ContextMenu:
    """The menu a right-click opens, shared by every list and tree, with its entries in the order shown.

    An entry is chosen by a click where it stands, which closes the menu the way a person's click
    does, and the menu is put away by a click beside it, on the bare stretch of the tab bar past the
    last tab.
    """

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self._hand = hand

    def is_shown(self) -> bool:
        return self._bridge.ask(lambda: read_item(TAG_GLOBAL_CONTEXT_WINDOW)).shown

    def box(self) -> Rect:
        """Where the menu stands in the viewport."""
        rect = self._bridge.ask(lambda: read_item(TAG_GLOBAL_CONTEXT_WINDOW)).rect
        if rect is None:
            raise MissingEntryError("The context menu stands nowhere")

        return rect

    def entries(self) -> List[EntryReading]:
        return list(self._bridge.ask(lambda: read_popup_entries(TAG_GLOBAL_CONTEXT_WINDOW)))

    def labels(self) -> List[str]:
        return [entry.label for entry in self.entries()]

    def submenus(self) -> List[str]:
        """The labels of the submenus the menu offers, in the order shown."""

        def read() -> List[str]:
            return [
                read_label(child)
                for child in dpg.get_item_children(TAG_GLOBAL_CONTEXT_WINDOW, 1)
                if dpg.get_item_info(child)["type"] == MENU_TYPE
            ]

        return self._bridge.ask(read)

    def submenu(self, label: str) -> List[Tuple[str, bool]]:
        """The entries of the submenu reading ``label``, each with whether it answers.

        Raises:
            MissingEntryError: If the menu offers no such submenu.
        """

        def read() -> Optional[List[Tuple[str, bool]]]:
            for child in dpg.get_item_children(TAG_GLOBAL_CONTEXT_WINDOW, 1):
                if dpg.get_item_info(child)["type"] == MENU_TYPE and read_label(child) == label:
                    return [
                        (read_label(entry), bool(dpg.get_item_configuration(entry).get(ENABLED, True)))
                        for entry in dpg.get_item_children(child, 1)
                        if dpg.get_item_info(entry)["type"] == MENU_ITEM_TYPE
                    ]

            return None

        found = self._bridge.ask(read)
        if found is None:
            raise MissingEntryError(f"The context menu offers no submenu '{label}'")

        return found

    def choose_in(
        self,
        menu_label: str,
        entry_label: str,
    ) -> None:
        """Opens the submenu reading ``menu_label`` with a click on it, and chooses its entry reading ``entry_label``.

        DearPyGui reports where a submenu's entries stand inside a window of its own that it names
        nowhere, so the entry is chosen by running its callback the way a click does. The menu is then
        put away by a click beside it, as a click on the entry would put it away.

        Raises:
            MissingEntryError: If the menu offers no such submenu.
        """
        header = self._submenu_header(menu_label)
        self._hand.click_at(Point(x=header.x + ENTRY_INSET.x, y=header.y + ENTRY_INSET.y))
        self._bridge.frames(OPENING_FRAMES)
        self._bridge.ask(lambda: invoke(self._submenu_entry(menu_label, entry_label), CallbackQueue.run))
        if self.is_shown():
            self.dismiss()

    def choose(self, label: str) -> None:
        """Clicks the entry reading ``label``.

        Raises:
            MissingEntryError: If the menu offers no such entry.
        """
        for entry in self.entries():
            if entry.label == label:
                self._hand.click_at(Point(x=entry.point.x + ENTRY_INSET.x, y=entry.point.y + ENTRY_INSET.y))
                return

        raise MissingEntryError(f"The context menu offers no '{label}': it offers {self.labels()}")

    def _submenu_header(self, label: str) -> Point:
        """Where the submenu reading ``label`` stands in the viewport."""

        def read() -> Optional[Point]:
            corner = dpg.get_item_pos(TAG_GLOBAL_CONTEXT_WINDOW)
            for child in dpg.get_item_children(TAG_GLOBAL_CONTEXT_WINDOW, 1):
                if dpg.get_item_info(child)["type"] == MENU_TYPE and read_label(child) == label:
                    position = dpg.get_item_state(child)["pos"]
                    return Point(x=round(corner[0] + position[0]), y=round(corner[1] + position[1]))

            return None

        found = self._bridge.ask(read)
        if found is None:
            raise MissingEntryError(f"The context menu offers no submenu '{label}'")

        return found

    @staticmethod
    def _submenu_entry(
        menu_label: str,
        entry_label: str,
    ) -> Item:
        """The entry reading ``entry_label`` of the submenu reading ``menu_label``. Runs on the render thread."""
        menu = find_labelled(TAG_GLOBAL_CONTEXT_WINDOW, menu_label, item_type=MENU_TYPE)
        return find_labelled(menu, entry_label, item_type=MENU_ITEM_TYPE)

    def dismiss(self) -> None:
        """Clicks the bare stretch of the tab bar past the last tab, which puts the menu away."""
        rect = self._bridge.ask(lambda: read_item(TAG_GLOBAL_TAB_INSTRUCTIONS)).rect
        if rect is None:
            raise MissingEntryError("The last tab stands nowhere to click past it")

        self._hand.click_at(Point(x=round(rect.x + rect.width) + CLEAR_OF_THE_TABS, y=rect.center.y))
