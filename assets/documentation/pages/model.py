from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import FrozenSet, List, Optional

from markdown_it.token import Token


@dataclass(frozen=True)
class ParsedPage:
    """A document read and its headings anchored, before its links are resolved.

    Attributes:
        relative: The document's path relative to the docs folder.
        tokens: The document's tokens, each heading carrying its anchor as its ``id``.
        anchors: Every anchor the document's headings hold.
        title: The document's title, its first-level heading as written.
    """

    relative: PurePosixPath
    tokens: List[Token]
    anchors: FrozenSet[str]
    title: str


@dataclass(frozen=True)
class Section:
    """One card of a page: a second-level heading and what follows it, or what precedes the first.

    Attributes:
        title_html: The heading as inline markup, or ``None`` for the opening card.
        anchor: The heading's anchor, or ``None`` for the opening card.
        body_html: Everything the section holds, as markup.
    """

    title_html: Optional[str]
    anchor: Optional[str]
    body_html: str
