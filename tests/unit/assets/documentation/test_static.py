import re
from pathlib import Path
from typing import Final, Set

from assets.documentation.build import DOCUMENTATION_STYLESHEET, TEMPLATE_FILE
from assets.documentation.paths import STATIC_DIRECTORY
from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
from sampletones_tools.web.design import ApplicationDesign
from sampletones_tools.web.writer import write_layout

COLOR_LITERAL: Final[re.Pattern[str]] = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")
USED: Final[re.Pattern[str]] = re.compile(r"var\(--([a-z0-9-]+)\)")
DECLARED: Final[re.Pattern[str]] = re.compile(r"--([a-z0-9-]+):")
PLACEHOLDER: Final[re.Pattern[str]] = re.compile(r"\$\{?(\w+)")
TEMPLATE_FIELDS: Final[Set[str]] = {
    "title",
    "heading",
    "stylesheets",
    "root",
    "layout",
    "navigation",
    "content",
    "version",
    "source",
}


def stylesheet() -> str:
    return (STATIC_DIRECTORY / DOCUMENTATION_STYLESHEET).read_text(encoding="utf-8")


class TestDocumentationStylesheet:
    def test_no_color_is_written_into_it(self) -> None:
        assert COLOR_LITERAL.findall(stylesheet()) == []

    def test_every_variable_it_reads_is_declared_by_the_layout(self, tmp_path: Path) -> None:
        write_layout(tmp_path, ApplicationDesign.load(DEFAULT_PALETTE_NAME))
        declared: Set[str] = set()
        for written in tmp_path.glob("*.css"):
            declared.update(DECLARED.findall(written.read_text(encoding="utf-8")))

        assert sorted(set(USED.findall(stylesheet())) - declared) == []


class TestPageTemplate:
    def test_it_names_exactly_the_fields_a_page_fills(self) -> None:
        template = (STATIC_DIRECTORY / TEMPLATE_FILE).read_text(encoding="utf-8")

        assert set(PLACEHOLDER.findall(template)) == TEMPLATE_FIELDS
