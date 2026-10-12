from pathlib import Path, PurePosixPath
from typing import Final, List, Set

from markdown_it import MarkdownIt
from markdown_it.token import Token

from assets.documentation.markdown.anchors import HeadingAnchors
from assets.documentation.pages.model import ParsedPage

HEADING_OPEN: Final[str] = "heading_open"
TITLE_LEVEL: Final[str] = "h1"
ANCHOR_ATTRIBUTE: Final[str] = "id"


class MissingTitleError(ValueError):
    pass


def parse_page(
    parser: MarkdownIt,
    docs: Path,
    relative: PurePosixPath,
) -> ParsedPage:
    """Read one document and give each heading its anchor, the fragment links to it name.

    Raises:
        MissingTitleError: If the document holds no first-level heading.
    """
    tokens = parser.parse((docs / relative).read_text(encoding="utf-8"))
    anchors = HeadingAnchors()
    claimed: Set[str] = set()
    for index, token in enumerate(tokens):
        if token.type == HEADING_OPEN:
            anchor = anchors.claim(tokens[index + 1].content)
            token.attrSet(ANCHOR_ATTRIBUTE, anchor)
            claimed.add(anchor)

    return ParsedPage(
        relative=relative,
        tokens=tokens,
        anchors=frozenset(claimed),
        title=_title(tokens, relative),
    )


def _title(tokens: List[Token], relative: PurePosixPath) -> str:
    for index, token in enumerate(tokens):
        if token.type == HEADING_OPEN and token.tag == TITLE_LEVEL:
            return tokens[index + 1].content

    raise MissingTitleError(f"{relative} holds no first-level heading to name its page by")
