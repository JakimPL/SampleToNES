import re
from dataclasses import dataclass
from html import escape, unescape
from pathlib import PurePosixPath
from string import Template
from typing import Final, Tuple
from urllib.parse import urljoin

TAG: Final[re.Pattern[str]] = re.compile(r"<[^>]+>")
LAYOUT_DIRECTORY: Final[str] = "style"
PARENT_STEP: Final[str] = "../"


@dataclass(frozen=True)
class PageChrome:
    """What every page shares around its content: the version, where the documentation lives
    online, and the stylesheets the page links, in order."""

    version: str
    address: str
    stylesheets: Tuple[str, ...]


@dataclass(frozen=True)
class PageContent:
    """What one page holds: its document, its title as inline markup, its navigation and its cards."""

    relative: PurePosixPath
    title_html: str
    navigation_html: str
    cards_html: str


def render_page(
    template: Template,
    chrome: PageChrome,
    content: PageContent,
) -> str:
    """The page as a complete document, every link to the shared files relative to where it sits."""
    root = PARENT_STEP * (len(content.relative.parts) - 1)
    stylesheets = "\n".join(
        f'<link rel="stylesheet" href="{root}{LAYOUT_DIRECTORY}/{name}">' for name in chrome.stylesheets
    )
    return template.substitute(
        title=escape(unescape(TAG.sub("", content.title_html))),
        heading=content.title_html,
        stylesheets=stylesheets,
        root=root,
        layout=LAYOUT_DIRECTORY,
        navigation=content.navigation_html,
        content=content.cards_html,
        version=escape(chrome.version),
        source=escape(urljoin(chrome.address.rstrip("/") + "/", content.relative.as_posix())),
    )
