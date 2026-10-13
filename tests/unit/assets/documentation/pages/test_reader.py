from pathlib import Path, PurePosixPath

import pytest
from markdown_it import MarkdownIt

from assets.documentation.pages.reader import MissingTitleError, parse_page


class TestParsePage:
    def test_every_heading_carries_its_anchor(self, parser: MarkdownIt, docs: Path) -> None:
        page = parse_page(parser, docs, PurePosixPath("guide/start.md"))
        identifiers = [token.attrGet("id") for token in page.tokens if token.type == "heading_open"]

        assert identifiers == ["start-here", "first-part", "first-part-1"]
        assert page.anchors == frozenset(identifiers)

    def test_the_title_is_the_first_level_heading(self, parser: MarkdownIt, docs: Path) -> None:
        assert parse_page(parser, docs, PurePosixPath("guide/start.md")).title == "Start here"

    def test_a_document_without_a_title_is_refused(self, parser: MarkdownIt, docs: Path) -> None:
        (docs / "guide" / "untitled.md").write_text("## Only a section\n", encoding="utf-8")

        with pytest.raises(MissingTitleError):
            parse_page(parser, docs, PurePosixPath("guide/untitled.md"))
