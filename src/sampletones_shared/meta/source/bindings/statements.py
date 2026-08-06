import ast
from typing import NamedTuple, Optional, Union

from sampletones_shared.meta.source.annotations import annotation_type_name
from sampletones_shared.meta.source.nodes import expression_spelling, terminal_name


class TypeStatement(NamedTuple):
    """A statement naming the type one spelling holds."""

    spelling: str
    type_name: str


class AliasStatement(NamedTuple):
    """A statement giving one spelling whatever type another spelling holds."""

    target: str
    source: str


class LoopStatement(NamedTuple):
    """A statement binding a target to the items of a container."""

    target: ast.expr
    iterable: ast.expr


Statement = Union[TypeStatement, AliasStatement, LoopStatement]


def read_statement(node: ast.AST) -> Optional[Statement]:
    """What one node states about the type of a spelling.

    A parameter annotation and an annotated assignment each name a type outright. An assignment
    from a direct construction names the constructed type, while an assignment from another
    spelling passes that spelling's type along. A `for` statement and a comprehension bind their
    target to the items of the container they walk.

    Args:
        node: Node to read.

    Returns:
        Optional[Statement]: What the node states, or `None` where it states nothing about a type.
    """
    match node:
        case ast.arg(arg=name, annotation=ast.expr() as annotation):
            return _annotated(name, annotation)
        case ast.AnnAssign(target=target, annotation=annotation):
            return _annotated_target(target, annotation)
        case ast.Assign(targets=[target], value=value):
            return _assigned(target, value)
        case ast.For(target=target, iter=iterable) | ast.comprehension(target=target, iter=iterable):
            return LoopStatement(
                target=target,
                iterable=iterable,
            )
        case _:
            return None


def _annotated(spelling: str, annotation: ast.expr) -> Optional[TypeStatement]:
    type_name = annotation_type_name(annotation)
    if type_name is None:
        return None

    return TypeStatement(
        spelling=spelling,
        type_name=type_name,
    )


def _annotated_target(target: ast.expr, annotation: ast.expr) -> Optional[TypeStatement]:
    spelling = expression_spelling(target)
    if spelling is None:
        return None

    return _annotated(spelling, annotation)


def _assigned(target: ast.expr, value: ast.expr) -> Optional[Statement]:
    spelling = expression_spelling(target)
    if spelling is None:
        return None

    match value:
        case ast.Call(func=func):
            return _constructed(spelling, func)
        case ast.Name() | ast.Attribute():
            return _aliased(spelling, value)
        case _:
            return None


def _constructed(spelling: str, func: ast.expr) -> Optional[TypeStatement]:
    constructed = terminal_name(func)
    if constructed is None:
        return None

    return TypeStatement(
        spelling=spelling,
        type_name=constructed,
    )


def _aliased(spelling: str, value: ast.expr) -> Optional[AliasStatement]:
    source = expression_spelling(value)
    if source is None:
        return None

    return AliasStatement(
        target=spelling,
        source=source,
    )
