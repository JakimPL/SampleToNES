from typing import Final, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import TAG_GLOBAL_CONTEXT_WINDOW, TAG_GLOBAL_TAB_INSTRUCTIONS
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.geometry import Point, Rect
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items import (
    MENU_ITEM_TYPE,
    MENU_TYPE,
    EntryReading,
    read_item,
    read_label,
    read_popup_entries,
)

ENTRY_INSET: Final[Point] = Point(x=12, y=8)
CLEAR_OF_THE_TABS: Final[int] = 48
ENABLED: Final[str] = "enabled"


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

    def dismiss(self) -> None:
        """Clicks the bare stretch of the tab bar past the last tab, which puts the menu away."""
        rect = self._bridge.ask(lambda: read_item(TAG_GLOBAL_TAB_INSTRUCTIONS)).rect
        if rect is None:
            raise MissingEntryError("The last tab stands nowhere to click past it")

        self._hand.click_at(Point(x=round(rect.x + rect.width) + CLEAR_OF_THE_TABS, y=rect.center.y))
