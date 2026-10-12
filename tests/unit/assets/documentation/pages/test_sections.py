from pathlib import PurePosixPath
from typing import Dict

from markdown_it import MarkdownIt

from assets.documentation.pages.model import ParsedPage
from assets.documentation.pages.sections import image_sources, split_sections

START = PurePosixPath("guide/start.md")
NEXT = PurePosixPath("guide/next.md")


class TestSplitSections:
    def test_the_opening_comes_first_and_each_section_follows(
        self,
        parser: MarkdownIt,
        pages: Dict[PurePosixPath, ParsedPage],
    ) -> None:
        sections = split_sections(parser, pages[START].tokens, {})

        assert [section.anchor for section in sections] == [None, "first-part", "first-part-1"]
        assert sections[0].title_html is None
        assert "Before the first section." in sections[0].body_html
        assert "Start here" not in "".join(section.body_html for section in sections)

    def test_a_section_holds_what_follows_its_heading(
        self,
        parser: MarkdownIt,
        pages: Dict[PurePosixPath, ParsedPage],
    ) -> None:
        sections = split_sections(parser, pages[START].tokens, {})

        assert sections[1].title_html == "First part"
        assert "<img" in sections[1].body_html
        assert "<table" in sections[2].body_html

    def test_an_empty_opening_makes_no_card(
        self,
        parser: MarkdownIt,
        pages: Dict[PurePosixPath, ParsedPage],
    ) -> None:
        sections = split_sections(parser, pages[NEXT].tokens, {})

        assert [section.anchor for section in sections] == ["second-part"]

    def test_a_heading_keeps_its_inline_markup(self, parser: MarkdownIt) -> None:
        tokens = parser.parse("# Title\n\n## The `.nsf` file\n\nText.\n")
        for token in tokens:
            if token.type == "heading_open":
                token.attrSet("id", "anchor")

        sections = split_sections(parser, tokens, {})

        assert sections[0].title_html == "The <code>.nsf</code> file"


class TestImageSources:
    def test_every_picture_is_named_as_written(self, pages: Dict[PurePosixPath, ParsedPage]) -> None:
        assert image_sources(pages[START].tokens) == ["../images/picture.webp"]

    def test_a_page_without_pictures_names_none(self, pages: Dict[PurePosixPath, ParsedPage]) -> None:
        assert image_sources(pages[NEXT].tokens) == []
