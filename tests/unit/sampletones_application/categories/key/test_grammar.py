import re
from dataclasses import dataclass
from typing import Optional, Type

import pytest

from sampletones_application.categories.elements.global_ import DialogElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.key.grammar import (
    TEXT_KEY_GRAMMAR,
    TEXT_KEY_SEGMENT_COUNT,
    validate_text_key,
)
from sampletones_application.categories.key.text import TextKey
from sampletones_shared.exceptions import MalformedTextKeyError
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.errors import expect_error


class TestValidateTextKey(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        key: str
        expected: Optional[Type[MalformedTextKeyError]]

    test_cases = [
        TestCase(label="well_formed_key", key="global.dialog.label.ok", expected=None),
        TestCase(label="element_holding_digits", key="global.context.label.pulse_1", expected=None),
        TestCase(label="element_holding_many_words", key="main.config.tooltip.window_size_input", expected=None),
        TestCase(label="another_page_and_panel", key="sequencer.grid.title.pattern", expected=None),
        TestCase(label="too_few_segments", key="global.dialog.label", expected=MalformedTextKeyError),
        TestCase(label="too_many_segments", key="global.dialog.label.ok.extra", expected=MalformedTextKeyError),
        TestCase(label="single_segment", key="ok", expected=MalformedTextKeyError),
        TestCase(label="empty_key", key="", expected=MalformedTextKeyError),
        TestCase(label="empty_segment", key="global..label.ok", expected=MalformedTextKeyError),
        TestCase(label="leading_separator", key=".global.dialog.label", expected=MalformedTextKeyError),
        TestCase(label="trailing_separator", key="global.dialog.label.", expected=MalformedTextKeyError),
        TestCase(label="unknown_page", key="globl.dialog.label.ok", expected=MalformedTextKeyError),
        TestCase(label="unknown_panel", key="global.dialogue.label.ok", expected=MalformedTextKeyError),
        TestCase(label="unknown_text_type", key="global.dialog.lable.ok", expected=MalformedTextKeyError),
        TestCase(label="widget_in_place_of_text_type", key="global.dialog.button.ok", expected=MalformedTextKeyError),
        TestCase(label="uppercase_key", key="GLOBAL.DIALOG.LABEL.OK", expected=MalformedTextKeyError),
        TestCase(label="uppercase_element", key="global.dialog.label.OK", expected=MalformedTextKeyError),
        TestCase(label="whitespace_in_element", key="global.dialog.label.o k", expected=MalformedTextKeyError),
        TestCase(label="surrounding_whitespace", key=" global.dialog.label.ok ", expected=MalformedTextKeyError),
        TestCase(label="template_in_element", key="global.dialog.label.{name}", expected=MalformedTextKeyError),
        TestCase(label="hyphen_in_element", key="global.dialog.label.not-ok", expected=MalformedTextKeyError),
        TestCase(label="doubled_underscore", key="global.dialog.label.not__ok", expected=MalformedTextKeyError),
        TestCase(label="leading_underscore", key="global.dialog.label._ok", expected=MalformedTextKeyError),
        TestCase(label="trailing_underscore", key="global.dialog.label.ok_", expected=MalformedTextKeyError),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_validate_text_key(self, test_case: TestCase) -> None:
        if not expect_error(validate_text_key, test_case.expected, test_case.key):
            assert validate_text_key(test_case.key) is None

    def test_every_page_and_text_type_member_is_accepted(self) -> None:
        for page in Page:
            for text_type in TextType:
                validate_text_key(f"{page}.dialog.{text_type}.element")

    def test_every_named_panel_is_accepted(self) -> None:
        for panel in Panel:
            if panel is Panel.IMPLICIT:
                continue

            validate_text_key(f"global.{panel}.label.element")


class TestMalformedTextKeyMessage:
    """A rejection has to say which segment failed and what would satisfy it."""

    def test_segment_count_message_counts_the_segments(self) -> None:
        with pytest.raises(MalformedTextKeyError, match=rf"segment count is 3.*exactly {TEXT_KEY_SEGMENT_COUNT}"):
            validate_text_key("global.dialog.label")

    def test_segment_count_message_spells_the_grammar_out(self) -> None:
        with pytest.raises(MalformedTextKeyError, match=re.escape(TEXT_KEY_GRAMMAR)):
            validate_text_key("global.dialog.label")

    def test_slug_message_names_the_offending_position(self) -> None:
        with pytest.raises(MalformedTextKeyError, match=r"segment 4 'Ok'"):
            validate_text_key("global.dialog.label.Ok")

    def test_unknown_page_message_lists_the_accepted_pages(self) -> None:
        with pytest.raises(MalformedTextKeyError, match=r"segment 1 'globl' must name a page.*global.*settings"):
            validate_text_key("globl.dialog.label.ok")

    def test_unknown_panel_message_lists_the_accepted_panels(self) -> None:
        with pytest.raises(MalformedTextKeyError, match=r"segment 2 'dialogue' must name a panel.*dialog"):
            validate_text_key("global.dialogue.label.ok")

    def test_unknown_text_type_message_lists_the_accepted_text_types(self) -> None:
        with pytest.raises(MalformedTextKeyError, match=r"segment 3 'lable' must name a text type.*label.*filter"):
            validate_text_key("global.dialog.lable.ok")


class TestTextKeyGrammar:
    def test_grammar_names_the_key_fields_in_order(self) -> None:
        assert TEXT_KEY_GRAMMAR == "page.panel.text_type.element"

    def test_segment_count_matches_the_grammar(self) -> None:
        assert TEXT_KEY_SEGMENT_COUNT == len(TEXT_KEY_GRAMMAR.split("."))

    def test_a_composed_key_satisfies_the_grammar(self) -> None:
        key = TextKey(Page.GLOBAL, Panel.DIALOG, TextType.LABEL, DialogElements.CANCEL)
        assert validate_text_key(key.compose()) is None
