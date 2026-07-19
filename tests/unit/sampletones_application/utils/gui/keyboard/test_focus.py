from dataclasses import dataclass
from typing import List, Optional

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard import focus


@dataclass(frozen=True)
class FocusCase:
    label: str
    focused_item: int
    item_type: Optional[str]
    is_active: bool
    expected: bool


CASES: List[FocusCase] = [
    FocusCase("nothing focused", 0, None, False, False),
    FocusCase("actively edited text input", 5, "mvAppItemType::mvInputText", True, True),
    FocusCase("focused but idle text input", 5, "mvAppItemType::mvInputText", False, False),
    FocusCase("actively edited integer input", 6, "mvAppItemType::mvInputInt", True, True),
    FocusCase("open combo", 7, "mvAppItemType::mvCombo", True, True),
    FocusCase("focused button", 9, "mvAppItemType::mvButton", True, False),
    FocusCase("idle slider", 11, "mvAppItemType::mvSliderInt", False, False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.label)
def test_is_field_focused(case: FocusCase, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dpg, "get_focused_item", lambda: case.focused_item)
    monkeypatch.setattr(dpg, "get_item_type", lambda item: case.item_type)
    monkeypatch.setattr(dpg, "is_item_active", lambda item: case.is_active)

    assert focus.is_field_focused() == case.expected
