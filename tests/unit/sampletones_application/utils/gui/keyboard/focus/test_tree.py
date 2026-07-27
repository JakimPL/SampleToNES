from typing import Any, Dict, List

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard.focus.tree import (
    focused_item,
    is_item_active,
    is_item_focused,
    item_exists,
    read_item,
)
from tests.unit.sampletones_application.utils.gui.keyboard.focus.item_tree import (
    GROUP,
    INPUT_TEXT,
    TABLE_ROW,
    FakeItemTree,
    container,
    editing,
    transparent,
)

ITEM = 7


class TestFocusedItem:
    def test_a_reported_item_is_returned(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(dpg, "get_focused_item", lambda: ITEM)

        assert focused_item() == ITEM

    def test_an_unset_focus_reads_as_no_item(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """DearPyGui reports the absence of a focused item as ``0``, which is no item at all."""
        monkeypatch.setattr(dpg, "get_focused_item", lambda: 0)

        assert focused_item() is None


class TestItemExists:
    def test_a_live_item_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        FakeItemTree({ITEM: editing(INPUT_TEXT)}, focused_item=ITEM).install(monkeypatch)

        assert item_exists(ITEM)

    def test_an_item_the_sequencer_rebuilt_away_is_gone(self, monkeypatch: pytest.MonkeyPatch) -> None:
        FakeItemTree({}, focused_item=ITEM).install(monkeypatch)

        assert not item_exists(ITEM)


class TestReadItem:
    def test_the_type_and_children_are_read_together(self, monkeypatch: pytest.MonkeyPatch) -> None:
        tree = FakeItemTree(
            {
                1: container(GROUP, 2, 3, focused=True, active=True),
                2: editing(INPUT_TEXT),
                3: editing(INPUT_TEXT),
            },
            focused_item=1,
        )
        tree.install(monkeypatch)

        node = read_item(1)

        assert node.item == 1
        assert node.item_type == GROUP
        assert node.children == [2, 3]

    def test_children_are_gathered_across_every_slot(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Children live in per-purpose slots, and the search reaches the widgets in each of them."""
        slots: Dict[int, List[int]] = {0: [4], 1: [5, 6], 2: [7]}
        monkeypatch.setattr(dpg, "get_item_info", lambda item: {"type": GROUP, "children": slots})

        node = read_item(1)

        assert sorted(node.children) == [4, 5, 6, 7]


class TestInteractionState:
    def test_an_edited_field_reports_focus_and_interaction(self, monkeypatch: pytest.MonkeyPatch) -> None:
        FakeItemTree({ITEM: editing(INPUT_TEXT)}, focused_item=ITEM).install(monkeypatch)

        assert is_item_active(ITEM)
        assert is_item_focused(ITEM)

    def test_a_container_without_interaction_state_reads_as_idle(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Item state is per-type, so a table row carries neither flag and answers ``False`` for both."""
        FakeItemTree({ITEM: transparent(TABLE_ROW)}, focused_item=ITEM).install(monkeypatch)

        assert not is_item_active(ITEM)
        assert not is_item_focused(ITEM)

    def test_a_state_entry_of_another_type_reads_as_idle(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """DearPyGui answers a state query with a per-type dictionary of mixed value types."""
        state: Dict[str, Any] = {"active": [0, 0], "focused": None}
        monkeypatch.setattr(dpg, "get_item_state", lambda item: state)

        assert not is_item_active(ITEM)
        assert not is_item_focused(ITEM)
