import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterable, List

from sampletones_shared.meta.source.nodes import PositionedNode

SOURCE_PATTERN: Final[str] = "*.py"
SOURCE_ENCODING: Final[str] = "utf-8-sig"
HIDDEN_PREFIX: Final[str] = "."
PACKAGE_INITIALIZER: Final[str] = "__init__"
MODULE_SEPARATOR: Final[str] = "."


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


def module_name(path: Path, root: Path) -> str:
    """The dotted name an import statement reaches a source file by.

    A check that finds a module by reading it can then reach the objects it declares, which is what
    lets a static sweep and a runtime read describe the same module.

    Args:
        path: Source file under the root.
        root: Directory imports resolve from, such as the source root.

    Returns:
        str: The dotted name, where a package's `__init__.py` names the package itself.

    Raises:
        ValueError: If the file sits outside the root.
    """
    relative = path.relative_to(root).with_suffix("")
    parts = relative.parts[:-1] if relative.name == PACKAGE_INITIALIZER else relative.parts
    return MODULE_SEPARATOR.join(parts)


def is_visible(path: Path) -> bool:
    """States whether every component of a path is a visible name."""
    return all(not part.startswith(HIDDEN_PREFIX) for part in path.parts)


def source_paths(roots: Iterable[Path]) -> List[Path]:
    """Every Python file under the given roots, in path order.

    The sweep visits visible paths, so a virtual environment or a tooling cache sitting inside a
    root stays aside from a whole-repository run. A check built on a sweep that reads nothing
    reports nothing, which reads as a clean tree, so each root must name a directory and the roots
    together must hold source to read.

    Args:
        roots: Directories to search.

    Returns:
        List[Path]: The paths found, each listed once however many roots hold it.

    Raises:
        NotADirectoryError: If a root names something other than a directory, such as the
            `__init__.py` a package resource resolves to.
        FileNotFoundError: If the roots together hold no Python file.
    """
    directories = list(roots)
    for root in directories:
        if not root.is_dir():
            raise NotADirectoryError(f"The source root {root} names no directory to sweep")

    found = {path for root in directories for path in root.rglob(SOURCE_PATTERN) if is_visible(path)}
    if not found:
        listed = ", ".join(str(root) for root in directories)
        raise FileNotFoundError(f"The source roots hold no {SOURCE_PATTERN} file to read: {listed}")

    return sorted(found)


def discover_modules(roots: Iterable[Path]) -> List[SourceModule]:
    """Parses every Python file under the given roots, in path order.

    Args:
        roots: Directories to search.

    Returns:
        List[SourceModule]: One entry per file found.

    Raises:
        NotADirectoryError: If a root names something other than a directory.
        FileNotFoundError: If the roots together hold no Python file.
        SyntaxError: If a file holds source Python rejects.
    """
    return [parse_module(path) for path in source_paths(roots)]
