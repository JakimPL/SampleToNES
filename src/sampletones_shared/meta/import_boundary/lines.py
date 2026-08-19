from pathlib import Path
from typing import Iterator, Tuple

from sampletones_shared.meta.source.modules import SOURCE_ENCODING


def numbered_lines(path: Path) -> Iterator[Tuple[int, str]]:
    """Each line of a module paired with the number a report points a reader at.

    A boundary is stated over the source as it is written rather than over the tree it parses to,
    so a report quotes the line a reader opens and an unparseable module is still checked.

    Args:
        path: Module to read.

    Yields:
        Tuple[int, str]: The line number, counting from one, and the line.

    Raises:
        OSError: If the module cannot be read.
    """
    yield from enumerate(
        path.read_text(encoding=SOURCE_ENCODING).splitlines(),
        start=1,
    )
