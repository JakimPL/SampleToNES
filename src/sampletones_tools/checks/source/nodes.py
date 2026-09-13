import ast
from typing import Final, Iterator, Optional, Tuple, Type, Union

PositionedNode = Union[ast.stmt, ast.expr]

SCOPE_NODES: Final[Tuple[Type[ast.AST], ...]] = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)

ATTRIBUTE_SEPARATOR: Final[str] = "."


def own_nodes(scope: ast.AST) -> Iterator[ast.AST]:
    """The scope itself and every node under it, up to where a nested scope begins.

    A function and a lambda each open a scope of their own, so their parameters and bodies belong
    to that scope rather than to the one holding them.

    Args:
        scope: Module, function, or lambda whose own region to walk.

    Yields:
        ast.AST: The scope node, then each node it owns.
    """
    yield scope
    for child in ast.iter_child_nodes(scope):
        if not isinstance(child, SCOPE_NODES):
            yield from own_nodes(child)


def nested_scopes(scope: ast.AST) -> Iterator[ast.AST]:
    """Every scope a scope opens directly, reached through the statements it owns.

    Args:
        scope: Module, function, or lambda to read.

    Yields:
        ast.AST: Each function or lambda the scope holds, before any deeper nesting.
    """
    for child in ast.iter_child_nodes(scope):
        if isinstance(child, SCOPE_NODES):
            yield child
        else:
            yield from nested_scopes(child)


def slice_elements(subscript: ast.Subscript) -> Tuple[ast.expr, ...]:
    """The expressions a subscript holds between its brackets, one per comma-separated part."""
    if isinstance(subscript.slice, ast.Tuple):
        return tuple(subscript.slice.elts)

    return (subscript.slice,)


def expression_spelling(node: ast.expr) -> Optional[str]:
    """The dotted source spelling of a name or an attribute chain, such as `self._manager`.

    Args:
        node: Expression to spell.

    Returns:
        Optional[str]: The spelling, or `None` where the expression is built from anything besides
            names and attributes.
    """
    match node:
        case ast.Name(id=name):
            return name
        case ast.Attribute(value=value, attr=attribute):
            base = expression_spelling(value)
            return None if base is None else f"{base}{ATTRIBUTE_SEPARATOR}{attribute}"
        case _:
            return None


def is_attribute_spelling(spelling: str) -> bool:
    """Whether a spelling reaches an attribute of something, as `self._manager` does.

    Args:
        spelling: Spelling to read, as `expression_spelling` writes it.

    Returns:
        bool: True where the spelling names an attribute, false where it names a bare name.
    """
    return ATTRIBUTE_SEPARATOR in spelling


def terminal_name(node: ast.expr) -> Optional[str]:
    """The last identifier of a name or an attribute chain, so `typing.Optional` states `Optional`.

    Args:
        node: Expression to read the identifier from.

    Returns:
        Optional[str]: The identifier, or `None` where the expression names none.
    """
    match node:
        case ast.Name(id=name):
            return name
        case ast.Attribute(attr=name):
            return name
        case _:
            return None
