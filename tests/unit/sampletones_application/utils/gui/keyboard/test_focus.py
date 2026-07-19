from dataclasses import dataclass
from typing import List, Optional

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard import focus


@dataclass(frozen=True)
class FocusCase:
    label: str
    focused_item: int
    exists: bool
    item_type: Optional[str]
    is_active: bool
    expected: bool


CASES: List[FocusCase] = [
    FocusCase("nothing focused", 0, False, None, False, False),
    FocusCase("actively edited text input", 5, True, "mvAppItemType::mvInputText", True, True),
    FocusCase("focused but idle text input", 5, True, "mvAppItemType::mvInputText", False, False),
    FocusCase("actively edited integer input", 6, True, "mvAppItemType::mvInputInt", True, True),
    FocusCase("open combo", 7, True, "mvAppItemType::mvCombo", True, True),
    FocusCase("focused button", 9, True, "mvAppItemType::mvButton", True, False),
    FocusCase("idle slider", 11, True, "mvAppItemType::mvSliderInt", False, False),
    FocusCase("stale item destroyed by a table rebuild", 94818, False, None, False, False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.label)
def test_is_field_focused(case: FocusCase, monkeypatch: pytest.MonkeyPatch) -> None:
    def item_type(_item: int) -> Optional[str]:
        if not case.exists:
            raise Exception("Item not found")
        return case.item_type

    monkeypatch.setattr(dpg, "get_focused_item", lambda: case.focused_item)
    monkeypatch.setattr(dpg, "does_item_exist", lambda item: case.exists)
    monkeypatch.setattr(dpg, "get_item_type", item_type)
    monkeypatch.setattr(dpg, "is_item_active", lambda _item: case.is_active)

    assert focus.is_field_focused() == case.expected
