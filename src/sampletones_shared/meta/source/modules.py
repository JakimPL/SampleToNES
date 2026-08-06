import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterable, List

from sampletones_shared.meta.source.nodes import PositionedNode

SOURCE_PATTERN: Final[str] = "*.py"
SOURCE_ENCODING: Final[str] = "utf-8-sig"
HIDDEN_PREFIX: Final[str] = "."


@dataclass(frozen=True)
class SourceModule:
    """One parsed Python file, together with the path a report names it by."""

    path: Path
    tree: ast.Module

    def location(self, node: PositionedNode) -> str:
        """Spells where a node sits as `path:line`, the form an editor jumps to."""
        return f"{self.path}:{node.lineno}"


def parse_module(path: Path) -> SourceModule:
    """Parses one Python file into a tree.

    The file is decoded as `utf-8-sig`, which reads both plain UTF-8 and a byte-order-marked file.

    Args:
        path: File to read.

    Returns:
        SourceModule: The file paired with its tree.

    Raises:
        SyntaxError: If the file holds source Python rejects.
    """
    source = path.read_text(encoding=SOURCE_ENCODING)
    return SourceModule(
        path=path,
        tree=ast.parse(
            source,
            filename=str(path),
        ),
    )


def is_visible(path: Path) -> bool:
    """States whether every component of a path is a visible name."""
    return all(not part.startswith(HIDDEN_PREFIX) for part in path.parts)


def source_paths(roots: Iterable[Path]) -> List[Path]:
    """Every Python file under the given roots, in path order.

    The sweep visits visible paths, so a virtual environment or a tooling cache sitting inside a
    root stays aside from a whole-repository run.

    Args:
        roots: Directories to search.

    Returns:
        List[Path]: The paths found, each listed once however many roots hold it.
    """
    found = {path for root in roots for path in root.rglob(SOURCE_PATTERN) if is_visible(path)}
    return sorted(found)


def discover_modules(roots: Iterable[Path]) -> List[SourceModule]:
    """Parses every Python file under the given roots, in path order.

    Args:
        roots: Directories to search.

    Returns:
        List[SourceModule]: One entry per file found.

    Raises:
        SyntaxError: If a file holds source Python rejects.
    """
    return [parse_module(path) for path in source_paths(roots)]
