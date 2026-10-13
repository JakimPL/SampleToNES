import posixpath
from html import escape
from pathlib import PurePosixPath
from typing import Callable, Final, List, Sequence

from assets.documentation.navigation import Navigation, NavigationEntry
from assets.documentation.pages.model import Section
from assets.documentation.published import INDEX_PAGE, page_path

InlineRenderer = Callable[[str], str]

HOME_TITLE: Final[str] = "Overview"


def navigation_html(
    navigation: Navigation,
    current: PurePosixPath,
    sections: Sequence[Section],
    inline: InlineRenderer,
) -> str:
    """The navigation as seen from page ``current``: the overview, then each group, every entry a
    link relative to the page, and the current page marked, with its sections listed beneath it."""
    lines: List[str] = [_home(current)]
    for group in navigation.groups:
        lines.append('<section class="navigation-group">')
        lines.append(f'<h2 class="navigation-heading">{inline(group.title)}</h2>')
        lines.append("<ul>")
        lines.extend(_entry(entry, current, sections, inline) for entry in group.entries)
        lines.append("</ul>")
        lines.append("</section>")

    return "\n".join(lines)


def _home(current: PurePosixPath) -> str:
    marked = ' aria-current="page"' if current == INDEX_PAGE else ""
    return f'<a class="navigation-home" href="{escape(_link(INDEX_PAGE, current))}"{marked}>{HOME_TITLE}</a>'


def _link(
    page: PurePosixPath,
    current: PurePosixPath,
) -> str:
    return posixpath.relpath(page_path(page).as_posix(), current.parent.as_posix())


def _entry(
    entry: NavigationEntry,
    current: PurePosixPath,
    sections: Sequence[Section],
    inline: InlineRenderer,
) -> str:
    link = _link(entry.page, current)
    title = inline(entry.title)
    if entry.page != current:
        return f'<li><a href="{escape(link)}">{title}</a></li>'

    anchors = "".join(
        f'<li><a href="#{escape(section.anchor)}">{section.title_html}</a></li>'
        for section in sections
        if section.anchor is not None and section.title_html is not None
    )
    listed = f'<ul class="navigation-anchors">{anchors}</ul>' if anchors else ""
    return f'<li class="current"><a href="{escape(link)}" aria-current="page">{title}</a>{listed}</li>'
