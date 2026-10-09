import ast
from collections import Counter
from typing import Dict


def count_identifier_loads(tree: ast.Module) -> Dict[str, int]:
    """Counts how often a module reads each identifier.

    A read is `NAME` where an expression evaluates it, or `.NAME` where an object exposes it.
    Only reads raise a count, so a constant declared here and read nowhere stands at zero, while a
    constant that feeds another constant's value counts once for that use.

    Args:
        tree: Parsed module to read.

    Returns:
        Dict[str, int]: Identifier to the number of times the module reads it.
    """
    counts: Counter[str] = Counter()
    for node in ast.walk(tree):
        match node:
            case ast.Name(id=name, ctx=ast.Load()):
                counts[name] += 1
            case ast.Attribute(attr=name, ctx=ast.Load()):
                counts[name] += 1

    return dict(counts)
