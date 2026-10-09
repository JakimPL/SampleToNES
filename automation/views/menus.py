from dataclasses import dataclass
from typing import Final, List

import dearpygui.dearpygui as dpg

from automation.dearpygui.bridge import Bridge
from automation.dearpygui.geometry import Point
from automation.dearpygui.hand import Hand
from automation.dearpygui.items.reading import read_item, read_value
from automation.dearpygui.items.texts import find_labelled, read_label
from automation.dearpygui.items.types import MENU_ITEM_TYPE, MENU_TYPE, Item
from automation.dearpygui.items.viewport import read_viewport
from automation.dearpygui.semantic import invoke
from automation.frames import changed_box, frame_pixels, settled_frame
from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.tags.general import (
    TAG_GLOBAL_TAB_INSTRUCTIONS,
    TAG_GLOBAL_TEXT_MENU_FPS,
    TAG_GLOBAL_WINDOW_MAIN,
)
from sampletones_application.utils.callbacks.queue import CallbackQueue

HEADER_INSET: Final[Point] = Point(x=12, y=8)
ENTRY_INSET: Final[Point] = Point(x=12, y=8)
HOVER_SECONDS: Final[float] = 5.0
ENABLED: Final[str] = "enabled"
SHORTCUT: Final[str] = "shortcut"
GROUP_TYPE: Final[str] = "mvAppItemType::mvGroup"
FAR_END_INSET: Final[int] = 30


@dataclass(frozen=True)
class MenuEntry:
    """One entry of a menu on the bar: its words, whether it answers, the keys printed beside it, and its check mark."""

    label: str
    enabled: bool
    keys: str
    checked: bool


class MenuBar:
    """The menu bar along the top of the window, read by the words its menus show.

    A menu and its entry are found by their labels, which the language file gives, so a scenario
    names an entry the way a user reads it. DearPyGui reports a menu entry's position alone, so
    choosing one runs its callback the way a click on it does.
    """

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
        language: LanguageManager,
    ) -> None:
        self._bridge = bridge
        self._hand = hand
        self._language = language

    def choose(
        self,
        group: MenuElements,
        item: MenuElements,
    ) -> None:
        """Chooses the entry ``item`` of the menu ``group``."""
        self._bridge.ask(lambda: invoke(self._entry(group, item), CallbackQueue.run))

    def choose_tagged(self, tag: str) -> None:
        """Chooses the entry carrying ``tag``, which reaches an entry whose words another entry shares."""
        self._bridge.ask(lambda: invoke(tag, CallbackQueue.run))

    def is_tagged_enabled(self, tag: str) -> bool:
        """Whether the entry carrying ``tag`` answers a press."""
        return self._bridge.ask(lambda: read_item(tag).enabled)

    def frame_rate_reading_shown(self) -> bool:
        """Whether the reading of the frame rate stands at the far end of the bar."""
        return self._bridge.ask(lambda: read_item(TAG_GLOBAL_TEXT_MENU_FPS)).shown

    def open(self, group: MenuElements) -> None:
        """Clicks the header of the menu ``group``, which opens its popup."""
        corner = self.header(group)
        self._hand.click_at(Point(x=corner.x + HEADER_INSET.x, y=corner.y + HEADER_INSET.y))

    def header(self, group: MenuElements) -> Point:
        """Where the header of the menu ``group`` stands on the bar, its top left corner."""
        corner = self._bridge.ask(lambda: dpg.get_item_state(self._menu(group))["pos"])
        return Point(x=round(corner[0]), y=round(corner[1]))

    def open_submenu(
        self,
        group: MenuElements,
        submenu: MenuElements,
    ) -> None:
        """Opens the menu ``group`` and rests the pointer on its entry ``submenu``, which unfolds the submenu.

        DearPyGui reports where an entry stands inside its popup alone, and the popup nowhere, so the
        popup is found by what it painted over the frame before it opened: its left edge is the painted
        box's, and its top stands its own height above the box's bottom. Both frames are read once the
        screen holds still, and the first frame DearPyGui hands over in a process is bare, so one reading
        is let go first.
        """
        frame_pixels(self._bridge)
        before = settled_frame(self._bridge)
        self.open(group)
        self._bridge.expect(
            lambda: self.is_open(group),
            bool,
            description=f"the {self.label(group)} menu open",
            timeout=HOVER_SECONDS,
        )
        painted = changed_box(before, settled_frame(self._bridge))
        height = self._bridge.ask(lambda: float(dpg.get_item_state(self._menu(group))["rect_size"][1]))
        offset = self._bridge.ask(lambda: dpg.get_item_state(self._submenu(group, submenu))["pos"])
        self._hand.move_to(
            Point(
                x=round(painted.x + offset[0] + ENTRY_INSET.x),
                y=round(painted.y + painted.height - height + offset[1] + ENTRY_INSET.y),
            )
        )
        self._bridge.expect(
            lambda: self.submenu_unfolded(group, submenu),
            bool,
            description=f"{self.label(submenu)} unfolded",
            timeout=HOVER_SECONDS,
        )

    def is_open(self, group: MenuElements) -> bool:
        """Whether the menu ``group`` stands open, which gives its popup a size."""
        return bool(self._bridge.ask(lambda: dpg.get_item_state(self._menu(group))["rect_size"][1] > 0))

    def submenu_unfolded(
        self,
        group: MenuElements,
        submenu: MenuElements,
    ) -> bool:
        """Whether the submenu ``submenu`` of the menu ``group`` stands unfolded, which gives its popup a size."""
        return bool(self._bridge.ask(lambda: dpg.get_item_state(self._submenu(group, submenu))["rect_size"][1] > 0))

    def close(self) -> None:
        """Clicks the bare far end of the tab bar, clear of every menu's popup, which puts an open menu away."""
        last_tab = self._bridge.ask(lambda: read_item(TAG_GLOBAL_TAB_INSTRUCTIONS).rect)
        viewport = self._bridge.ask(read_viewport)
        if last_tab is None:
            raise LookupError("The last tab reports no box to click beside")

        self._hand.click_at(Point(x=round(viewport.width) - FAR_END_INSET, y=last_tab.center.y))

    def entries(self, group: MenuElements) -> List[MenuEntry]:
        """The entries of the menu ``group``, in order: their words, whether they answer, and the keys printed."""

        def read() -> List[MenuEntry]:
            return [
                MenuEntry(
                    label=read_label(entry),
                    enabled=bool(dpg.get_item_configuration(entry).get(ENABLED, True)),
                    keys=str(dpg.get_item_configuration(entry).get(SHORTCUT, "")),
                    checked=bool(read_value(entry)),
                )
                for entry in _menu_items(self._menu(group))
            ]

        return self._bridge.ask(read)

    def is_enabled(
        self,
        group: MenuElements,
        item: MenuElements,
    ) -> bool:
        """Whether the entry ``item`` of the menu ``group`` answers a press."""
        return self._bridge.ask(lambda: read_item(self._entry(group, item)).enabled)

    def is_checked(
        self,
        group: MenuElements,
        item: MenuElements,
    ) -> bool:
        """Whether the entry ``item`` of the menu ``group`` carries its check mark."""
        return bool(self._bridge.ask(lambda: read_value(self._entry(group, item))))

    def _menu(self, group: MenuElements) -> Item:
        """The menu ``group`` on the bar. Runs on the render thread."""
        return find_labelled(TAG_GLOBAL_WINDOW_MAIN, self.label(group), item_type=MENU_TYPE)

    def _submenu(
        self,
        group: MenuElements,
        submenu: MenuElements,
    ) -> Item:
        """The entry of the menu ``group`` that unfolds the submenu ``submenu``. Runs on the render thread."""
        return find_labelled(self._menu(group), self.label(submenu), item_type=MENU_TYPE)

    def _entry(
        self,
        group: MenuElements,
        item: MenuElements,
    ) -> Item:
        """The entry ``item`` of the menu ``group``. Runs on the render thread."""
        menu = find_labelled(
            TAG_GLOBAL_WINDOW_MAIN,
            self.label(group),
            item_type=MENU_TYPE,
        )
        return find_labelled(
            menu,
            self.label(item),
            item_type=MENU_ITEM_TYPE,
        )

    def label(self, element: MenuElements) -> str:
        """The words the menu bar shows for ``element``."""
        return self._language[
            Page.GLOBAL,
            Panel.MENU,
            TextType.LABEL,
            element,
        ]


def _menu_items(menu: Item) -> List[Item]:
    """The entries under ``menu`` in the order drawn, those of its groups among them. Runs on the render thread."""
    found: List[Item] = []
    for child in dpg.get_item_children(menu, 1):
        kind = dpg.get_item_info(child)["type"]
        if kind == MENU_ITEM_TYPE:
            found.append(child)
        elif kind == GROUP_TYPE:
            found.extend(_menu_items(child))

    return found
