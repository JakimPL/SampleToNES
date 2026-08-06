from dataclasses import dataclass
from pathlib import Path
from typing import Final, List, Tuple

import pytest

from sampletones_application.categories.hierarchy import Page, Panel, Widget
from sampletones_application.categories.key.tag import TagName
from sampletones_shared.meta.source.modules import SourceModule
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.scripts import load_script
from tests.suite.source import parse_source

check_tag_names = load_script("scripts/checks/tag_names.py")

MODULE_PATH: Final[Path] = Path("src/sampletones_application/tags/general.py")

WINDOW_TAG: Final[str] = 'TagName(Page.GLOBAL, Panel.IMPLICIT, Widget.WINDOW, "main")'


def messages(source: str) -> List[str]:
    module = SourceModule(path=MODULE_PATH, tree=parse_source(source))
    return [finding.message for finding in check_tag_names.check_module(module)]


class TestExpectedName:
    def test_an_implicit_panel_leaves_the_name_at_page_and_widget(self) -> None:
        tag = TagName(Page.GLOBAL, Panel.IMPLICIT, Widget.WINDOW, "main")
        assert check_tag_names.expected_name(tag) == "TAG_GLOBAL_WINDOW_MAIN"

    def test_a_named_panel_stands_between_the_page_and_the_widget(self) -> None:
        tag = TagName(Page.MAIN, Panel.CONVERTER, Widget.BUTTON, "convert")
        assert check_tag_names.expected_name(tag) == "TAG_MAIN_CONVERTER_BUTTON_CONVERT"

    def test_an_empty_element_leaves_the_name_at_the_widget(self) -> None:
        tag = TagName(Page.GLOBAL, Panel.IMPLICIT, Widget.TABS, "")
        assert check_tag_names.expected_name(tag) == "TAG_GLOBAL_TABS"


class TestCheckModule(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        source: str
        expected: Tuple[str, ...]

    test_cases = [
        TestCase(
            label="well_named_tag",
            source=f"TAG_GLOBAL_WINDOW_MAIN = {WINDOW_TAG}",
            expected=(),
        ),
        TestCase(
            label="mistyped_name",
            source=f"TAG_GLOBAL_WINDOW_MIAN = {WINDOW_TAG}",
            expected=("TAG_GLOBAL_WINDOW_MAIN",),
        ),
        TestCase(
            label="keyword_arguments",
            source=(
                "TAG_GLOBAL_WINDOW_MAIN = TagName(\n"
                "    page=Page.GLOBAL,\n"
                "    panel=Panel.IMPLICIT,\n"
                "    widget=Widget.WINDOW,\n"
                '    element="main",\n'
                ")"
            ),
            expected=(),
        ),
        TestCase(
            label="mistyped_name_with_keyword_arguments",
            source=(
                "TAG_GLOBAL_WINDOW_OTHER = TagName(\n"
                "    page=Page.GLOBAL,\n"
                "    panel=Panel.IMPLICIT,\n"
                "    widget=Widget.WINDOW,\n"
                '    element="main",\n'
                ")"
            ),
            expected=("TAG_GLOBAL_WINDOW_MAIN",),
        ),
        TestCase(
            label="annotated_assignment",
            source=f"TAG_GLOBAL_WINDOW_MAIN: Final[TagName] = {WINDOW_TAG}",
            expected=(),
        ),
        TestCase(
            label="chained_assignment_checks_every_name",
            source=f"TAG_GLOBAL_WINDOW_MAIN = TAG_WINDOW_ALIAS = {WINDOW_TAG}",
            expected=("TAG_WINDOW_ALIAS",),
        ),
        TestCase(
            label="panel_shortened_to_its_element",
            source='TAG_MAIN_CONFIG_PANEL = TagName(Page.MAIN, Panel.CONFIG, Widget.PANEL, "config")',
            expected=(),
        ),
        TestCase(
            label="element_taken_from_a_constant",
            source="TAG_GLOBAL_WINDOW_MAIN = TagName(Page.GLOBAL, Panel.IMPLICIT, Widget.WINDOW, SUF_MAIN)",
            expected=("reads no tag from",),
        ),
        TestCase(
            label="member_outside_the_hierarchy",
            source='TAG_NOWHERE_WINDOW_MAIN = TagName(Page.NOWHERE, Panel.IMPLICIT, Widget.WINDOW, "main")',
            expected=("reads no tag from",),
        ),
        TestCase(
            label="missing_argument",
            source="TAG_GLOBAL_WINDOW_MAIN = TagName(Page.GLOBAL, Panel.IMPLICIT, Widget.WINDOW)",
            expected=("reads no arguments from",),
        ),
        TestCase(
            label="arguments_unpacked_from_a_sequence",
            source="TAG_GLOBAL_WINDOW_MAIN = TagName(*parts)",
            expected=("reads no arguments from",),
        ),
        TestCase(
            label="fragment_holding_no_tag",
            source='SUF_BUTTON = "button"',
            expected=(),
        ),
        TestCase(
            label="call_of_another_kind",
            source="PALETTE = dict(main=1)",
            expected=(),
        ),
        TestCase(
            label="local_assignment_stays_in_its_function",
            source=f"def build() -> TagName:\n    tag = {WINDOW_TAG}\n    return tag",
            expected=(),
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_check_module(self, test_case: "TestCheckModule.TestCase") -> None:
        found = messages(test_case.source)

        assert len(found) == len(test_case.expected)
        for message, fragment in zip(found, test_case.expected, strict=True):
            assert fragment in message


class TestMain:
    def test_the_tags_package_names_its_tags_after_them(self) -> None:
        assert check_tag_names.main(["--all"]) == 0

    def test_a_mistyped_tag_is_reported_where_it_sits(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        module = tmp_path / "tags.py"
        module.write_text(f"TAG_GLOBAL_WINDOW_MIAN = {WINDOW_TAG}\n", encoding="utf-8")

        assert check_tag_names.main([str(module)]) == 1

        error = capsys.readouterr().err
        assert f"{module}:1" in error
        assert "TAG_GLOBAL_WINDOW_MAIN" in error

    def test_a_well_named_module_reports_nothing(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        module = tmp_path / "tags.py"
        module.write_text(f"TAG_GLOBAL_WINDOW_MAIN = {WINDOW_TAG}\n", encoding="utf-8")

        assert check_tag_names.main([str(module)]) == 0
        assert capsys.readouterr().err == ""
