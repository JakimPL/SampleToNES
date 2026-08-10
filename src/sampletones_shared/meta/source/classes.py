import ast
from typing import List

from sampletones_shared.meta.source.nodes import terminal_name


def declared_subclasses(tree: ast.Module, base: str) -> List[str]:
    """The classes a module declares over a named base, wherever in the module they sit.

    A base is matched by the identifier the class states it under, so a module reaching it through
    `from package import Base` and one writing `package.Base` are both read. This is what lets a
    check find a family of classes by what they derive from while they live wherever their domain
    lives.

    Args:
        tree: Parsed module to read.
        base: Identifier the base class is spelled by.

    Returns:
        List[str]: The class names, outermost declarations first.
    """
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and any(terminal_name(parent) == base for parent in node.bases)
    ]
