from dataclasses import dataclass

import pytest

from sampletones_application.utils.gui.keyboard.focus.items import (
    CHOICE_ITEM_TYPES,
    TEXT_ENTRY_ITEM_TYPES,
    field_kind,
    reports_child_focus,
)
from sampletones_application.utils.gui.keyboard.focus.kind import FieldKind
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.unit.sampletones_application.utils.gui.keyboard.focus.item_tree import (
    BUTTON,
    CHILD_WINDOW,
    COMBO,
    GROUP,
    INPUT_INT,
    INPUT_TEXT,
    SLIDER_INT,
    TAB,
    TAB_BAR,
    TABLE_ROW,
)

UNKNOWN_ITEM_TYPE = "mvAppItemType::mvSomethingNew"


class TestFieldKindOfItemType(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        item_type: str
        expected: FieldKind

    test_cases = [
        TestCase(label="text input types characters", item_type=INPUT_TEXT, expected=FieldKind.TEXT_ENTRY),
        TestCase(label="integer input types characters", item_type=INPUT_INT, expected=FieldKind.TEXT_ENTRY),
        TestCase(label="slider types characters", item_type=SLIDER_INT, expected=FieldKind.TEXT_ENTRY),
        TestCase(label="combo navigates options", item_type=COMBO, expected=FieldKind.CHOICE),
        TestCase(label="button keeps no keys", item_type=BUTTON, expected=FieldKind.NONE),
        TestCase(label="group keeps no keys", item_type=GROUP, expected=FieldKind.NONE),
        TestCase(label="unknown type keeps no keys", item_type=UNKNOWN_ITEM_TYPE, expected=FieldKind.NONE),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_field_kind(self, test_case: TestCase) -> None:
        assert field_kind(test_case.item_type) is test_case.expected


class TestTaxonomyCoverage:
    def test_every_text_entry_type_maps_to_text_entry(self) -> None:
        assert {field_kind(item_type) for item_type in TEXT_ENTRY_ITEM_TYPES} == {FieldKind.TEXT_ENTRY}

    def test_every_choice_type_maps_to_choice(self) -> None:
        assert {field_kind(item_type) for item_type in CHOICE_ITEM_TYPES} == {FieldKind.CHOICE}

    def test_the_two_field_taxonomies_stay_disjoint(self) -> None:
        assert TEXT_ENTRY_ITEM_TYPES.isdisjoint(CHOICE_ITEM_TYPES)


class TestReportsChildFocus(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        item_type: str
        expected: bool

    test_cases = [
        TestCase(label="group carries its children's state", item_type=GROUP, expected=True),
        TestCase(label="child window carries its children's state", item_type=CHILD_WINDOW, expected=True),
        TestCase(label="tab answers for its own header", item_type=TAB, expected=False),
        TestCase(label="tab bar answers for itself", item_type=TAB_BAR, expected=False),
        TestCase(label="table row answers for itself", item_type=TABLE_ROW, expected=False),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_reports_child_focus(self, test_case: TestCase) -> None:
        assert reports_child_focus(test_case.item_type) is test_case.expected
