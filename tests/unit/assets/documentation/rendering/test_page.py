from pathlib import PurePosixPath
from string import Template
from typing import List

import pytest

from assets.documentation.rendering.page import LAYOUT_DIRECTORY, PageChrome, PageContent, render_page

TEMPLATE = Template("$title|$heading|$stylesheets|$root|$layout|$navigation|$content|$version|$source")
CHROME = PageChrome(version="1.2.3", address="https://example.com/docs/", stylesheets=("a.css", "b.css"))


@pytest.fixture
def fields() -> List[str]:
    content = PageContent(
        relative=PurePosixPath("guide/start.md"),
        title_html="The <code>.nsf</code> &amp; more",
        navigation_html="NAVIGATION",
        cards_html="CARDS",
    )
    return render_page(TEMPLATE, CHROME, content).split("|")


class TestRenderPage:
    def test_the_tab_title_is_the_heading_as_text(self, fields: List[str]) -> None:
        assert fields[0] == "The .nsf &amp; more"
        assert fields[1] == "The <code>.nsf</code> &amp; more"

    def test_shared_files_are_linked_from_where_the_page_sits(self, fields: List[str]) -> None:
        assert fields[2] == (
            f'<link rel="stylesheet" href="../{LAYOUT_DIRECTORY}/a.css">\n'
            f'<link rel="stylesheet" href="../{LAYOUT_DIRECTORY}/b.css">'
        )
        assert fields[3] == "../"

    def test_the_online_copy_is_the_document_at_the_address(self, fields: List[str]) -> None:
        assert fields[8] == "https://example.com/docs/guide/start.md"

    def test_the_parts_land_in_their_places(self, fields: List[str]) -> None:
        assert fields[4:8] == [LAYOUT_DIRECTORY, "NAVIGATION", "CARDS", "1.2.3"]
