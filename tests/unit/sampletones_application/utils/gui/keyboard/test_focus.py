from dataclasses import dataclass
from typing import List, Optional

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard import focus
from sampletones_application.utils.gui.keyboard.focus import FieldKind


@dataclass(frozen=True)
class FocusCase:
    label: str
    focused_item: int
    exists: bool
    item_type: Optional[str]
    is_active: bool
    expected: FieldKind


CASES: List[FocusCase] = [
    FocusCase("nothing focused", 0, False, None, False, FieldKind.NONE),
    FocusCase("actively edited text input", 5, True, "mvAppItemType::mvInputText", True, FieldKind.TEXT_ENTRY),
    FocusCase("focused but idle text input", 5, True, "mvAppItemType::mvInputText", False, FieldKind.NONE),
    FocusCase("actively edited integer input", 6, True, "mvAppItemType::mvInputInt", True, FieldKind.TEXT_ENTRY),
    FocusCase("open combo", 7, True, "mvAppItemType::mvCombo", True, FieldKind.CHOICE),
    FocusCase("focused button", 9, True, "mvAppItemType::mvButton", True, FieldKind.NONE),
    FocusCase("idle slider", 11, True, "mvAppItemType::mvSliderInt", False, FieldKind.NONE),
    FocusCase("stale item destroyed by a table rebuild", 94818, False, None, False, FieldKind.NONE),
]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.label)
def test_focused_field_kind(case: FocusCase, monkeypatch: pytest.MonkeyPatch) -> None:
    def item_type(_item: int) -> Optional[str]:
        if not case.exists:
            raise Exception("Item not found")
        return case.item_type

    monkeypatch.setattr(dpg, "get_focused_item", lambda: case.focused_item)
    monkeypatch.setattr(dpg, "does_item_exist", lambda item: case.exists)
    monkeypatch.setattr(dpg, "get_item_type", item_type)
    monkeypatch.setattr(dpg, "is_item_active", lambda _item: case.is_active)

    assert focus.focused_field_kind() == case.expected
    assert focus.is_field_focused() == (case.expected is not FieldKind.NONE)


@dataclass(frozen=True)
class ConsumeCase:
    label: str
    kind: FieldKind
    key: int
    ctrl: bool
    shift: bool
    alt: bool
    expected: bool


CONSUME_CASES: List[ConsumeCase] = [
    ConsumeCase("no field lets every key through", FieldKind.NONE, dpg.mvKey_Spacebar, False, False, False, False),
    ConsumeCase("text field types a space", FieldKind.TEXT_ENTRY, dpg.mvKey_Spacebar, False, False, False, True),
    ConsumeCase("text field types a shifted space", FieldKind.TEXT_ENTRY, dpg.mvKey_Spacebar, False, True, False, True),
    ConsumeCase("text field yields Ctrl+Space", FieldKind.TEXT_ENTRY, dpg.mvKey_Spacebar, True, False, False, False),
    ConsumeCase(
        "text field yields Ctrl+Shift+Space", FieldKind.TEXT_ENTRY, dpg.mvKey_Spacebar, True, True, False, False
    ),
    ConsumeCase("text field cancels on Escape", FieldKind.TEXT_ENTRY, dpg.mvKey_Escape, False, False, False, True),
    ConsumeCase("text field commits on Enter", FieldKind.TEXT_ENTRY, dpg.mvKey_Return, False, False, False, True),
    ConsumeCase("text field selects all on Ctrl+A", FieldKind.TEXT_ENTRY, dpg.mvKey_A, True, False, False, True),
    ConsumeCase("text field undoes on Ctrl+Z", FieldKind.TEXT_ENTRY, dpg.mvKey_Z, True, False, False, True),
    ConsumeCase("text field redoes on Ctrl+Shift+Z", FieldKind.TEXT_ENTRY, dpg.mvKey_Z, True, True, False, True),
    ConsumeCase("text field yields Ctrl+S", FieldKind.TEXT_ENTRY, dpg.mvKey_S, True, False, False, False),
    ConsumeCase("text field yields Alt+F4", FieldKind.TEXT_ENTRY, dpg.mvKey_F4, False, False, True, False),
    ConsumeCase("text field yields F11", FieldKind.TEXT_ENTRY, dpg.mvKey_F11, False, False, False, False),
    ConsumeCase("open combo yields a plain space", FieldKind.CHOICE, dpg.mvKey_Spacebar, False, False, False, False),
    ConsumeCase("open combo closes on Escape", FieldKind.CHOICE, dpg.mvKey_Escape, False, False, False, True),
    ConsumeCase("open combo yields Ctrl+A", FieldKind.CHOICE, dpg.mvKey_A, True, False, False, False),
]


@pytest.mark.parametrize("case", CONSUME_CASES, ids=lambda case: case.label)
def test_field_consumes_key(case: ConsumeCase) -> None:
    assert (
        focus.field_consumes_key(case.kind, case.key, ctrl=case.ctrl, shift=case.shift, alt=case.alt) is case.expected
    )


def test_non_field_item_is_ruled_out_before_its_active_state_is_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """A focused selectable is ruled out by type, so its missing ``active`` state is never probed.

    Only field widgets report an ``active`` flag; reading it on a selectable raises ``KeyError``, so
    the type gate must reject non-field items before the active-state query runs.
    """

    def raise_missing_active(_item: int) -> bool:
        raise KeyError("active")

    monkeypatch.setattr(dpg, "get_focused_item", lambda: 42)
    monkeypatch.setattr(dpg, "does_item_exist", lambda _item: True)
    monkeypatch.setattr(dpg, "get_item_type", lambda _item: "mvAppItemType::mvSelectable")
    monkeypatch.setattr(dpg, "is_item_active", raise_missing_active)

    assert focus.focused_field_kind() is FieldKind.NONE
