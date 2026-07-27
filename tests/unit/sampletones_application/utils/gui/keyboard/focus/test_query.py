from dataclasses import dataclass
from typing import Dict

import pytest

from sampletones_application.utils.gui.keyboard.focus.kind import FieldKind
from sampletones_application.utils.gui.keyboard.focus.query import (
    focused_field_kind,
    is_field_focused,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.unit.sampletones_application.utils.gui.keyboard.focus.item_tree import (
    COMBO,
    INPUT_TEXT,
    INSTRUMENTS_CARD_BODY,
    SEQUENCE_ROW,
    TRACKER_CELLS,
    FakeItem,
    FakeItemTree,
    editing,
    idle,
)

NO_ITEM = 0
STALE_ITEM = 94818
FOCUSED = 1


class TestFocusedFieldKind(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        items: Dict[int, FakeItem]
        focused_item: int
        expected: FieldKind

    test_cases = [
        TestCase(label="nothing focused", items={}, focused_item=NO_ITEM, expected=FieldKind.NONE),
        TestCase(
            label="stale item destroyed by a table rebuild",
            items={},
            focused_item=STALE_ITEM,
            expected=FieldKind.NONE,
        ),
        TestCase(
            label="actively edited text input",
            items={FOCUSED: editing(INPUT_TEXT)},
            focused_item=FOCUSED,
            expected=FieldKind.TEXT_ENTRY,
        ),
        TestCase(
            label="focused but idle text input",
            items={FOCUSED: idle(INPUT_TEXT)},
            focused_item=FOCUSED,
            expected=FieldKind.NONE,
        ),
        TestCase(
            label="open combo",
            items={FOCUSED: editing(COMBO)},
            focused_item=FOCUSED,
            expected=FieldKind.CHOICE,
        ),
        TestCase(
            label="sequence input reported as its group",
            items=SEQUENCE_ROW,
            focused_item=FOCUSED,
            expected=FieldKind.TEXT_ENTRY,
        ),
        TestCase(
            label="sequence input reported as the instruments card body",
            items=INSTRUMENTS_CARD_BODY,
            focused_item=FOCUSED,
            expected=FieldKind.TEXT_ENTRY,
        ),
        TestCase(
            label="tracker cell holding the cursor",
            items=TRACKER_CELLS,
            focused_item=FOCUSED,
            expected=FieldKind.NONE,
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_focused_field_kind(self, test_case: TestCase, monkeypatch: pytest.MonkeyPatch) -> None:
        FakeItemTree(test_case.items, focused_item=test_case.focused_item).install(monkeypatch)

        assert focused_field_kind() is test_case.expected

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_is_field_focused_follows_the_kind(self, test_case: TestCase, monkeypatch: pytest.MonkeyPatch) -> None:
        FakeItemTree(test_case.items, focused_item=test_case.focused_item).install(monkeypatch)

        assert is_field_focused() == (test_case.expected is not FieldKind.NONE)
