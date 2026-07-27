from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard.focus import tree

BUTTON = "mvAppItemType::mvButton"
CHILD_WINDOW = "mvAppItemType::mvChildWindow"
COMBO = "mvAppItemType::mvCombo"
GROUP = "mvAppItemType::mvGroup"
INPUT_INT = "mvAppItemType::mvInputInt"
INPUT_TEXT = "mvAppItemType::mvInputText"
SELECTABLE = "mvAppItemType::mvSelectable"
SLIDER_INT = "mvAppItemType::mvSliderInt"
TAB = "mvAppItemType::mvTab"
TAB_BAR = "mvAppItemType::mvTabBar"
TABLE_ROW = "mvAppItemType::mvTableRow"

WIDGET_SLOT = 1


@dataclass(frozen=True)
class FakeItem:
    """One item of a stand-in widget tree, carrying the per-type state DearPyGui reports for it."""

    item_type: str
    children: Tuple[int, ...] = ()
    state: Dict[str, bool] = field(default_factory=dict)


def editing(item_type: str) -> FakeItem:
    """A widget the user is interacting with, as DearPyGui reports a field being typed into."""
    return FakeItem(item_type=item_type, state={tree.STATE_FOCUSED: True, tree.STATE_ACTIVE: True})


def idle(item_type: str) -> FakeItem:
    """A widget holding keyboard focus while the user interacts with nothing."""
    return FakeItem(item_type=item_type, state={tree.STATE_FOCUSED: True, tree.STATE_ACTIVE: False})


def container(item_type: str, *children: int, focused: bool, active: bool) -> FakeItem:
    """A container reporting the state DearPyGui aggregates from the widgets it lays out."""
    return FakeItem(
        item_type=item_type,
        children=children,
        state={tree.STATE_FOCUSED: focused, tree.STATE_ACTIVE: active},
    )


def transparent(item_type: str, *children: int) -> FakeItem:
    """A container that carries no interaction state of its own, as a table row and a tab bar do."""
    return FakeItem(item_type=item_type, children=children)


class FakeItemTree:
    """A stand-in DearPyGui item tree that records which items a focus query reads."""

    def __init__(self, items: Dict[int, FakeItem], focused_item: int) -> None:
        self._items = items
        self._focused_item = focused_item
        self.read_items: List[int] = []

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Answers every DearPyGui item query this tree stands in for."""
        monkeypatch.setattr(dpg, "get_focused_item", lambda: self._focused_item)
        monkeypatch.setattr(dpg, "does_item_exist", lambda item: item in self._items)
        monkeypatch.setattr(dpg, "get_item_info", self._info)
        monkeypatch.setattr(dpg, "get_item_state", self._state)

    def _info(self, item: int) -> Dict[str, Any]:
        self.read_items.append(item)
        fake = self._items[item]
        return {"type": fake.item_type, "children": {0: [], WIDGET_SLOT: list(fake.children)}}

    def _state(self, item: int) -> Dict[str, bool]:
        return dict(self._items[item].state)


SEQUENCE_ROW: Dict[int, FakeItem] = {
    1: container(GROUP, 2, 3, focused=True, active=True),
    2: idle(BUTTON),
    3: editing(INPUT_TEXT),
}

NESTED_GROUPS: Dict[int, FakeItem] = {
    1: container(GROUP, 2, focused=True, active=True),
    2: container(GROUP, 3, focused=True, active=True),
    3: editing(INPUT_TEXT),
}

GROUP_OVER_CARD: Dict[int, FakeItem] = {
    1: container(GROUP, 2, focused=True, active=True),
    2: container(CHILD_WINDOW, 3, focused=True, active=False),
    3: editing(INPUT_TEXT),
}

GROUP_OVER_TABLE_ROW: Dict[int, FakeItem] = {
    1: container(GROUP, 2, focused=True, active=True),
    2: transparent(TABLE_ROW, 3),
    3: editing(INPUT_TEXT),
}

UNFOCUSED_TAB_CONTENT = 11

INSTRUMENTS_CARD_BODY: Dict[int, FakeItem] = {
    1: container(GROUP, 2, focused=True, active=True),
    2: transparent(TAB_BAR, 3, 9),
    3: container(TAB, 4, focused=False, active=False),
    4: container(CHILD_WINDOW, 5, focused=True, active=False),
    5: container(GROUP, 6, focused=True, active=True),
    6: container(GROUP, 7, 8, focused=True, active=True),
    7: idle(BUTTON),
    8: editing(INPUT_TEXT),
    9: container(TAB, 10, focused=False, active=False),
    10: container(CHILD_WINDOW, UNFOCUSED_TAB_CONTENT, focused=False, active=False),
    UNFOCUSED_TAB_CONTENT: container(GROUP, focused=False, active=False),
}

TRACKER_CELLS: Dict[int, FakeItem] = {
    1: container(GROUP, 2, focused=True, active=False),
    2: container(GROUP, 3, focused=True, active=False),
    3: idle(SELECTABLE),
}

GROUP_HOLDING_A_PRESSED_BUTTON: Dict[int, FakeItem] = {
    1: container(GROUP, 2, focused=True, active=True),
    2: editing(BUTTON),
}
