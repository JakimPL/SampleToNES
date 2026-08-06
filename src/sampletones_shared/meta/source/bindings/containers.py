import ast
from typing import Dict, Final, FrozenSet, Mapping, NamedTuple, Optional, Tuple

from sampletones_shared.meta.source.annotations import annotation_item_types
from sampletones_shared.meta.source.nodes import expression_spelling

KEY_ACCESSOR: Final[str] = "keys"
VALUE_ACCESSOR: Final[str] = "values"
ITEM_ACCESSOR: Final[str] = "items"
CONTAINER_ACCESSORS: Final[FrozenSet[str]] = frozenset({KEY_ACCESSOR, VALUE_ACCESSOR, ITEM_ACCESSOR})

ITEM_TARGET_COUNT: Final[int] = 2

ItemTypes = Mapping[str, Tuple[str, ...]]


class IteratedContainer(NamedTuple):
    """The container a loop walks, and the accessor it walks it through."""

    spelling: str
    accessor: Optional[str]


class IteratedType(NamedTuple):
    """One loop target and the type the walked container gives it."""

    target: ast.expr
    type_name: str


def iterated_container(iterable: ast.expr) -> Optional[IteratedContainer]:
    """The container an iteration reads, walked directly or through `keys`, `values`, or `items`.

    Args:
        iterable: Expression a `for` statement or a comprehension walks.

    Returns:
        Optional[IteratedContainer]: The container and its accessor, or `None` where the iteration
            reads an expression built from anything besides names and attributes.
    """
    match iterable:
        case ast.Call(func=ast.Attribute(value=value, attr=accessor)) if accessor in CONTAINER_ACCESSORS:
            return _container(value, accessor)
        case _:
            return _container(iterable, None)


def iterated_types(
    target: ast.expr,
    accessor: Optional[str],
    item_types: Tuple[str, ...],
) -> Tuple[IteratedType, ...]:
    """The types a loop target takes from the container it walks.

    Walking `items()` types a pair of targets, the first from the key type and the second from the
    value type. Walking `values()` types the target from the value type, and every other walk types
    it from the key type, which is what a mapping and a sequence alike yield.

    Args:
        target: Expression a `for` statement or a comprehension binds.
        accessor: Accessor the iteration walks the container through, or `None` for a direct walk.
        item_types: Item types the container's annotation states.

    Returns:
        Tuple[IteratedType, ...]: One entry per target the walk types, holding entries where the
            container states item types and the target matches the shape the accessor yields.
    """
    if not item_types:
        return ()

    if accessor == ITEM_ACCESSOR:
        return _pair_types(target, item_types)

    if accessor == VALUE_ACCESSOR:
        return (IteratedType(target=target, type_name=item_types[-1]),)

    return (IteratedType(target=target, type_name=item_types[0]),)


def container_item_types(tree: ast.Module) -> Dict[str, Tuple[str, ...]]:
    """The item types every annotated container in a module states, keyed by its spelling.

    Args:
        tree: Parsed module to read.

    Returns:
        Dict[str, Tuple[str, ...]]: Container spelling to the item types its annotation states.
    """
    item_types: Dict[str, Tuple[str, ...]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            spelling = expression_spelling(node.target)
            items = annotation_item_types(node.annotation)
            if spelling is not None and items:
                item_types[spelling] = items

    return item_types


def _pair_types(target: ast.expr, item_types: Tuple[str, ...]) -> Tuple[IteratedType, ...]:
    if not (isinstance(target, ast.Tuple) and len(target.elts) == ITEM_TARGET_COUNT):
        return ()

    key_target, value_target = target.elts
    return (
        IteratedType(target=key_target, type_name=item_types[0]),
        IteratedType(target=value_target, type_name=item_types[-1]),
    )


def _container(value: ast.expr, accessor: Optional[str]) -> Optional[IteratedContainer]:
    spelling = expression_spelling(value)
    if spelling is None:
        return None

    return IteratedContainer(
        spelling=spelling,
        accessor=accessor,
    )
