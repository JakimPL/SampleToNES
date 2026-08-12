from dataclasses import dataclass
from typing import Final, Optional, Tuple

BLOCK_MAGIC: Final[str] = "SampleToNES/1"
ROW_KEY: Final[str] = "rows"
LABEL_SEPARATOR: Final[str] = "="
SPAN_SEPARATOR: Final[str] = ".."
HEADER_TOKEN_COUNT: Final[int] = 4


@dataclass(frozen=True)
class BlockShape:
    """How far a block reaches: the rows it holds, and the span its fields cross.

    The span is stated in the coordinates of the grid the block was read from, so a tracker
    block names the slots it began and ended on and a reading of it lands on the same kinds of
    subcolumn.
    """

    rows: int
    first: int
    last: int

    @property
    def width(self) -> int:
        return self.last - self.first + 1


def state_header(*, grid: str, span_key: str, shape: BlockShape) -> str:
    """The line a block opens with, naming the grid it came from and the shape it covers."""
    rows = f"{ROW_KEY}{LABEL_SEPARATOR}{shape.rows}"
    span = f"{span_key}{LABEL_SEPARATOR}{shape.first}{SPAN_SEPARATOR}{shape.last}"
    return f"{BLOCK_MAGIC} {grid} {rows} {span}"


def parse_header(
    line: str,
    *,
    grid: str,
    span_key: str,
) -> Optional[BlockShape]:
    """The shape a header states, present while it names this grid in the form written here.

    The shape is also the declaration the body is held to, so a text whose lines state a
    different count or width is refused by the reader that asked for it.
    """
    tokens = line.split()
    if len(tokens) != HEADER_TOKEN_COUNT or tokens[0] != BLOCK_MAGIC or tokens[1] != grid:
        return None

    rows = _read_count(tokens[2], ROW_KEY)
    span = _read_span(tokens[3], span_key)
    if rows is None or span is None:
        return None

    first, last = span
    return BlockShape(rows=rows, first=first, last=last)


def _read_label(token: str, label: str) -> Optional[str]:
    """What a ``label=value`` token states, present while it carries the label asked for."""
    name, separator, value = token.partition(LABEL_SEPARATOR)
    if name != label or not separator:
        return None

    return value


def _read_count(token: str, label: str) -> Optional[int]:
    """The count a ``rows=4`` token names, present while it covers at least one row."""
    value = _read_label(token, label)
    if value is None or not value.isdigit() or int(value) < 1:
        return None

    return int(value)


def _read_span(token: str, label: str) -> Optional[Tuple[int, int]]:
    """The bounds a ``slots=3..11`` token names, present while they stand in reading order."""
    value = _read_label(token, label)
    if value is None:
        return None

    first, separator, last = value.partition(SPAN_SEPARATOR)
    if not separator or not first.isdigit() or not last.isdigit() or int(last) < int(first):
        return None

    return int(first), int(last)
