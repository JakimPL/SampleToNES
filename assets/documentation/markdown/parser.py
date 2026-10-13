from typing import Final, Sequence

from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML
from markdown_it.token import Token
from markdown_it.utils import EnvType, OptionsDict

COMMONMARK: Final[str] = "commonmark"
TABLE_RULE: Final[str] = "table"
TABLE_OPEN: Final[str] = '<div class="table-scroll"><table class="table">\n'
TABLE_CLOSE: Final[str] = "</table></div>\n"


def markdown_parser() -> MarkdownIt:
    """The parser the documentation is read with: CommonMark, the pipe tables GitHub draws, and
    the raw HTML the pages hold for their pictures, with every table in the application's style."""
    parser = MarkdownIt(COMMONMARK, {"html": True}).enable(TABLE_RULE)
    parser.add_render_rule("table_open", _table_open)
    parser.add_render_rule("table_close", _table_close)
    return parser


def _table_open(
    _renderer: RendererHTML,
    _tokens: Sequence[Token],
    _index: int,
    _options: OptionsDict,
    _env: EnvType,
) -> str:
    return TABLE_OPEN


def _table_close(
    _renderer: RendererHTML,
    _tokens: Sequence[Token],
    _index: int,
    _options: OptionsDict,
    _env: EnvType,
) -> str:
    return TABLE_CLOSE
