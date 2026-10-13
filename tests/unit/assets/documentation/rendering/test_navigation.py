from pathlib import PurePosixPath

from assets.documentation.navigation import Navigation
from assets.documentation.pages.model import Section
from assets.documentation.rendering.navigation import HOME_TITLE, navigation_html

SECTIONS = (
    Section(title_html=None, anchor=None, body_html=""),
    Section(title_html="First part", anchor="first-part", body_html=""),
)


def inline(text: str) -> str:
    return text


class TestNavigationHtml:
    def test_links_are_relative_to_the_page(self, navigation: Navigation) -> None:
        html = navigation_html(navigation, PurePosixPath("guide/next.md"), SECTIONS, inline)

        assert f'<a class="navigation-home" href="../index.html">{HOME_TITLE}</a>' in html
        assert '<a href="start.html">Start here</a>' in html
        assert '<a href="../glossary.html">Glossary</a>' in html

    def test_the_current_page_is_marked_with_its_sections(self, navigation: Navigation) -> None:
        html = navigation_html(navigation, PurePosixPath("guide/start.md"), SECTIONS, inline)

        assert '<a href="start.html" aria-current="page">Start here</a>' in html
        assert '<ul class="navigation-anchors"><li><a href="#first-part">First part</a></li></ul>' in html
        assert html.count("aria-current") == 1

    def test_the_index_marks_the_overview(self, navigation: Navigation) -> None:
        html = navigation_html(navigation, PurePosixPath("index.md"), SECTIONS, inline)

        assert f'<a class="navigation-home" href="index.html" aria-current="page">{HOME_TITLE}</a>' in html
        assert "navigation-anchors" not in html

    def test_each_group_is_headed_by_its_title(self, navigation: Navigation) -> None:
        html = navigation_html(navigation, PurePosixPath("index.md"), SECTIONS, inline)

        assert '<h2 class="navigation-heading">Using it</h2>' in html
