import ast
from pathlib import Path
from typing import Dict, Final

HEXADECIMAL_MARKER: Final[str] = "$"
HEXADECIMAL_PREFIX: Final[str] = "0x"
ASSIGNMENT: Final[str] = "="


def _value(node: ast.expr, defined: Dict[str, int]) -> int:
    """The number an equate's expression comes to, over the equates before it."""
    match node:
        case ast.Constant(value=int() as number):
            return number
        case ast.Name(id=name):
            return defined[name]
        case ast.BinOp(left=left, op=ast.Add(), right=right):
            return _value(left, defined) + _value(right, defined)
        case ast.BinOp(left=left, op=ast.Sub(), right=right):
            return _value(left, defined) - _value(right, defined)
        case ast.BinOp(left=left, op=ast.Mult(), right=right):
            return _value(left, defined) * _value(right, defined)

    raise ValueError(f"an equate reads {ast.dump(node)}, which the include holds no form for")


def read_equates(path: Path) -> Dict[str, int]:
    """Reads the constants an assembly include states, each over the ones stated before it.

    The assembly and the exporter read the same blocks, so what the assembly believes about a
    layout is held against what the specification states. An include line is ``NAME = value``,
    where the value is a number, another equate, or the two joined by a sum, a difference or a
    product.

    Args:
        path: The include file to read.

    Returns:
        Dict[str, int]: The value each equate comes to.
    """
    defined: Dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ASSIGNMENT not in line:
            continue

        name, expression = line.split(ASSIGNMENT, 1)
        parsed = ast.parse(expression.strip().replace(HEXADECIMAL_MARKER, HEXADECIMAL_PREFIX), mode="eval")
        defined[name.strip()] = _value(parsed.body, defined)

    return defined
