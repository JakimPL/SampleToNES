from dataclasses import dataclass
from typing import Final, Union

import pytest

from sampletones_application.categories.elements.global_ import DialogElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.key.text import (
    TextKey,
    TextKeyTuple,
    compose_text_key,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

CANCEL_KEY: Final[TextKey] = TextKey(Page.GLOBAL, Panel.DIALOG, TextType.LABEL, DialogElements.CANCEL)


class TestTextKeyComposition:
    def test_compose_joins_all_four_parts(self) -> None:
        key = TextKey(Page.GLOBAL, Panel.DIALOG, TextType.LABEL, DialogElements.OK)
        assert key.compose() == "global.dialog.label.ok"

    def test_str_matches_compose(self) -> None:
        key = TextKey(Page.GLOBAL, Panel.DIALOG, TextType.TITLE, DialogElements.CANCEL)
        assert str(key) == key.compose()


class TestComposeTextKey(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        key: Union[str, TextKey, TextKeyTuple]
        expected: str

    test_cases = [
        TestCase(
            label="string_passes_through",
            key="global.dialog.label.cancel",
            expected="global.dialog.label.cancel",
        ),
        TestCase(
            label="text_key_composes",
            key=CANCEL_KEY,
            expected="global.dialog.label.cancel",
        ),
        TestCase(
            label="tuple_composes",
            key=(Page.GLOBAL, Panel.DIALOG, TextType.LABEL, DialogElements.CANCEL),
            expected="global.dialog.label.cancel",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_compose_text_key(self, test_case: TestCase) -> None:
        assert compose_text_key(test_case.key) == test_case.expected
