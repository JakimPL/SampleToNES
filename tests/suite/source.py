import ast
from pathlib import Path
from textwrap import dedent
from typing import Iterable, Set

from sampletones_shared.meta.source.bindings.scopes import Scope
from sampletones_shared.meta.source.modules import source_paths


def parse_source(source: str) -> ast.Module:
    """Parses a snippet written inline in a test, stripping the indentation the test file gives it."""
    return ast.parse(dedent(source))


def scope_named(scopes: Iterable[Scope], name: str) -> Scope:
    """The scope one function opens, found among the scopes of a module.

    Args:
        scopes: Scopes to search, as `module_scopes` reads them.
        name: Name of the function whose scope to take.

    Returns:
        Scope: The scope that function opens.

    Raises:
        AssertionError: If the scopes hold no function of that name.
    """
    for scope in scopes:
        if isinstance(scope.node, ast.FunctionDef) and scope.node.name == name:
            return scope

    raise AssertionError(f"the scopes hold no function named {name}")


def write_module(directory: Path, name: str, body: str) -> Path:
    """Writes one module into a tree a test builds, opening the directories it sits under.

    Args:
        directory: Directory the module belongs in.
        name: File name to write it under.
        body: Source the module holds.

    Returns:
        Path: Where the module was written.
    """
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(body, encoding="utf-8")
    return path


def swept_paths(root: Path) -> Set[Path]:
    """The resolved modules a sweep of one tree reads, the form a rule is held to.

    Args:
        root: Tree to sweep.

    Returns:
        Set[Path]: Every visible module under the tree, resolved.

    Raises:
        NotADirectoryError: If the root names no directory.
        FileNotFoundError: If the root holds no module to read.
    """
    return {path.resolve() for path in source_paths([root])}
