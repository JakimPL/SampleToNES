from markdown_it import MarkdownIt

from assets.documentation.markdown.parser import TABLE_CLOSE, TABLE_OPEN

TABLE = "| A | B |\n|---|---|\n| 1 | 2 |\n"


class TestMarkdownParser:
    def test_a_table_is_wrapped_to_scroll_on_its_own(self, parser: MarkdownIt) -> None:
        html = parser.render(TABLE)

        assert html.startswith(TABLE_OPEN)
        assert html.endswith(TABLE_CLOSE)
        assert "<td>1</td>" in html

    def test_raw_html_passes_through(self, parser: MarkdownIt) -> None:
        html = parser.render('<div align="center"><img src="picture.webp" alt="A picture"></div>\n')

        assert '<img src="picture.webp" alt="A picture">' in html
