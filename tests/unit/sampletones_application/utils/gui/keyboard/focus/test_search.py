from dataclasses import dataclass
from typing import Dict

import pytest

from sampletones_application.utils.gui.keyboard.focus.kind import FieldKind
from sampletones_application.utils.gui.keyboard.focus.search import edited_field_kind
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.unit.sampletones_application.utils.gui.keyboard.focus.item_tree import (
    BUTTON,
    COMBO,
    GROUP_HOLDING_A_PRESSED_BUTTON,
    GROUP_OVER_CARD,
    GROUP_OVER_TABLE_ROW,
    INPUT_INT,
    INPUT_TEXT,
    INSTRUMENTS_CARD_BODY,
    NESTED_GROUPS,
    SELECTABLE,
    SEQUENCE_ROW,
    SLIDER_INT,
    TRACKER_CELLS,
    UNFOCUSED_TAB_CONTENT,
    FakeItem,
    FakeItemTree,
    editing,
    idle,
)

FOCUSED = 1


class TestEditedFieldKind(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        items: Dict[int, FakeItem]
        expected: FieldKind

    test_cases = [
        TestCase(
            label="actively edited text input",
            items={FOCUSED: editing(INPUT_TEXT)},
            expected=FieldKind.TEXT_ENTRY,
        ),
        TestCase(
            label="actively edited integer input",
            items={FOCUSED: editing(INPUT_INT)},
            expected=FieldKind.TEXT_ENTRY,
        ),
        TestCase(
            label="open combo",
            items={FOCUSED: editing(COMBO)},
            expected=FieldKind.CHOICE,
        ),
        TestCase(
            label="focused but idle text input",
            items={FOCUSED: idle(INPUT_TEXT)},
            expected=FieldKind.NONE,
        ),
        TestCase(
            label="idle slider",
            items={FOCUSED: idle(SLIDER_INT)},
            expected=FieldKind.NONE,
        ),
        TestCase(
            label="pressed button",
            items={FOCUSED: editing(BUTTON)},
            expected=FieldKind.NONE,
        ),
        TestCase(
            label="focused selectable reporting no state",
            items={FOCUSED: FakeItem(SELECTABLE)},
            expected=FieldKind.NONE,
        ),
        TestCase(
            label="sequence input beside its copy button",
            items=SEQUENCE_ROW,
            expected=FieldKind.TEXT_ENTRY,
        ),
        TestCase(
            label="input under nested groups",
            items=NESTED_GROUPS,
            expected=FieldKind.TEXT_ENTRY,
        ),
        TestCase(
            label="input inside a card inside a group",
            items=GROUP_OVER_CARD,
            expected=FieldKind.TEXT_ENTRY,
        ),
        TestCase(
            label="input inside a table row inside a group",
            items=GROUP_OVER_TABLE_ROW,
            expected=FieldKind.TEXT_ENTRY,
        ),
        TestCase(
            label="sequence input under the instruments card body",
            items=INSTRUMENTS_CARD_BODY,
            expected=FieldKind.TEXT_ENTRY,
        ),
        TestCase(
            label="tracker cell holding the cursor",
            items=TRACKER_CELLS,
            expected=FieldKind.NONE,
        ),
        TestCase(
            label="group holding a pressed button",
            items=GROUP_HOLDING_A_PRESSED_BUTTON,
            expected=FieldKind.NONE,
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_edited_field_kind(self, test_case: TestCase, monkeypatch: pytest.MonkeyPatch) -> None:
        FakeItemTree(test_case.items, focused_item=FOCUSED).install(monkeypatch)

        assert edited_field_kind(FOCUSED) is test_case.expected


class TestSearchExtent:
    def test_the_search_follows_the_branch_that_reports_focus(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The instruments card body encloses every generator tab, and only the focused one is read.

        DearPyGui names the outermost group around an edited field as the focused item, so the search
        starts at a group spanning the whole panel. Following the branch that reports focus keeps the
        cost of a key press to the path down to the field.
        """
        tree = FakeItemTree(INSTRUMENTS_CARD_BODY, focused_item=FOCUSED)
        tree.install(monkeypatch)

        assert edited_field_kind(FOCUSED) is FieldKind.TEXT_ENTRY
        assert UNFOCUSED_TAB_CONTENT not in tree.read_items

    def test_an_idle_group_is_answered_without_reading_its_cells(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A tracker cursor leaves the grid focused while nothing is edited, and the cells stay unread.

        The sequencer holds a group around a table of hundreds of cells. An interaction anywhere
        below a group shows in the state the group reports, so an idle group answers for its whole
        subtree at once.
        """
        tree = FakeItemTree(TRACKER_CELLS, focused_item=FOCUSED)
        tree.install(monkeypatch)

        assert edited_field_kind(FOCUSED) is FieldKind.NONE
        assert tree.read_items == []
