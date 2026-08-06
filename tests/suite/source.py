import ast
from textwrap import dedent
from typing import Iterable

from sampletones_shared.meta.source.bindings.scopes import Scope


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
