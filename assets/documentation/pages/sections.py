import re
from dataclasses import dataclass, field
from typing import Final, List, Optional, Tuple

from markdown_it import MarkdownIt
from markdown_it.token import Token
from markdown_it.utils import EnvType

from assets.documentation.pages.model import Section

HEADING_OPEN: Final[str] = "heading_open"
HEADING_CLOSE: Final[str] = "heading_close"
TITLE_LEVEL: Final[str] = "h1"
SECTION_LEVEL: Final[str] = "h2"
ANCHOR_ATTRIBUTE: Final[str] = "id"
IMAGE_SOURCE: Final[re.Pattern[str]] = re.compile(r'<img\b[^>]*\bsrc="([^"]+)"')
HTML_TOKENS: Final[Tuple[str, ...]] = ("html_block", "html_inline")


@dataclass
class _Segment:
    title: Optional[Token]
    anchor: Optional[str]
    body: List[Token] = field(default_factory=list)


def split_sections(
    parser: MarkdownIt,
    tokens: List[Token],
    env: EnvType,
) -> List[Section]:
    """A page as its cards: what precedes the first second-level heading, then one card per such
    heading with what follows it. The first-level heading is the page's title and stands apart.

    An opening that holds nothing makes no card.
    """
    segments: List[_Segment] = [_Segment(title=None, anchor=None)]
    position = 0
    while position < len(tokens):
        token = tokens[position]
        if token.type == HEADING_OPEN and token.tag in (TITLE_LEVEL, SECTION_LEVEL):
            if token.tag == SECTION_LEVEL:
                anchor = token.attrGet(ANCHOR_ATTRIBUTE)
                segments.append(_Segment(title=tokens[position + 1], anchor=str(anchor)))
            position = _after_heading(tokens, position)
            continue

        segments[-1].body.append(token)
        position += 1

    return [_section(parser, segment, env) for segment in segments if segment.title is not None or segment.body]


def image_sources(tokens: List[Token]) -> List[str]:
    """The source of every picture the page holds as raw HTML, as the page writes it."""
    return [source for token in tokens if token.type in HTML_TOKENS for source in IMAGE_SOURCE.findall(token.content)]


def _after_heading(tokens: List[Token], position: int) -> int:
    while tokens[position].type != HEADING_CLOSE:
        position += 1

    return position + 1


def _section(
    parser: MarkdownIt,
    segment: _Segment,
    env: EnvType,
) -> Section:
    title_html = parser.renderer.render([segment.title], parser.options, env) if segment.title is not None else None
    return Section(
        title_html=title_html,
        anchor=segment.anchor,
        body_html=parser.renderer.render(segment.body, parser.options, env),
    )
