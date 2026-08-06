import ast
from dataclasses import dataclass
from typing import Dict, Final, FrozenSet, List, Mapping, NamedTuple, Optional, Tuple

from sampletones_shared.meta.source.annotations import annotation_item_types, annotation_type_name
from sampletones_shared.meta.source.nodes import expression_spelling, nested_scopes, own_nodes, terminal_name

ATTRIBUTE_SEPARATOR: Final[str] = "."

KEY_ACCESSOR: Final[str] = "keys"
VALUE_ACCESSOR: Final[str] = "values"
ITEM_ACCESSOR: Final[str] = "items"
CONTAINER_ACCESSORS: Final[FrozenSet[str]] = frozenset({KEY_ACCESSOR, VALUE_ACCESSOR, ITEM_ACCESSOR})

ITEM_TARGET_COUNT: Final[int] = 2


@dataclass(frozen=True)
class TypeEnvironment:
    """The types stated for the expressions a scope names.

    A spelling is a name or an attribute chain as the source writes it, so both `language_manager`
    and `self._language_manager` name the object a lookup reads from.
    """

    types: Mapping[str, str]

    def type_of(self, spelling: str) -> Optional[str]:
        """The type name stated for one spelling.

        Args:
            spelling: Name or attribute chain, such as `element` or `self._language_manager`.

        Returns:
            Optional[str]: The type name, or `None` where the scope states none.
        """
        return self.types.get(spelling)

    def spellings_of(self, type_name: str) -> Tuple[str, ...]:
        """Every spelling stated to hold the named type.

        Args:
            type_name: Simple type name, as an annotation writes it.

        Returns:
            Tuple[str, ...]: The spellings, ordered as they were read.
        """
        return tuple(spelling for spelling, name in self.types.items() if name == type_name)


@dataclass(frozen=True)
class Scope:
    """One lexical scope of a module — the module itself, a function, or a lambda."""

    node: ast.AST
    environment: TypeEnvironment


class IteratedContainer(NamedTuple):
    """The container a loop walks, and the accessor it walks it through."""

    spelling: str
    accessor: Optional[str]


class _Alias(NamedTuple):
    scope: int
    target: str
    source: str


class _Loop(NamedTuple):
    scope: int
    target: ast.expr
    iterable: ast.expr


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
            spelling = expression_spelling(value)
            return (
                None
                if spelling is None
                else IteratedContainer(
                    spelling=spelling,
                    accessor=accessor,
                )
            )
        case _:
            spelling = expression_spelling(iterable)
            return (
                None
                if spelling is None
                else IteratedContainer(
                    spelling=spelling,
                    accessor=None,
                )
            )


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


class _ModuleReader:
    """Reads the types a module states, scope by scope.

    A bare name belongs to the scope that declares it, so two methods may each take an `element`
    parameter of their own type. An attribute chain such as `self._manager` belongs to the module,
    which is what lets one method state the type another method reads.
    """

    def __init__(self, item_types: Mapping[str, Tuple[str, ...]]) -> None:
        self._item_types: Mapping[str, Tuple[str, ...]] = item_types
        self._attribute_types: Dict[str, str] = {}
        self._nodes: List[ast.AST] = []
        self._parents: List[Optional[int]] = []
        self._names: List[Dict[str, str]] = []
        self._aliases: List[_Alias] = []
        self._loops: List[_Loop] = []

    def read(self, node: ast.AST, parent: Optional[int]) -> None:
        """Reads one scope and every scope it opens.

        Args:
            node: Module, function, or lambda to read.
            parent: Index of the enclosing scope, or `None` for the module itself.
        """
        scope = len(self._nodes)
        self._nodes.append(node)
        self._parents.append(parent)
        self._names.append({})
        for owned in own_nodes(node):
            self._read_node(scope, owned)

        for nested in nested_scopes(node):
            self.read(nested, scope)

    def scopes(self) -> List[Scope]:
        """The scopes read so far, each holding the types visible inside it."""
        self._bind_loops()
        self._carry_aliases()
        return [
            Scope(node=node, environment=TypeEnvironment(types=self._visible(scope)))
            for scope, node in enumerate(self._nodes)
        ]

    def _read_node(self, scope: int, node: ast.AST) -> None:
        match node:
            case ast.arg(arg=name, annotation=ast.expr() as annotation):
                self._state(scope, name, annotation)
            case ast.AnnAssign(target=target, annotation=annotation):
                spelling = expression_spelling(target)
                if spelling is not None:
                    self._state(scope, spelling, annotation)
            case ast.Assign(targets=[target], value=value):
                self._read_assignment(scope, target, value)
            case ast.For(target=target, iter=iterable) | ast.comprehension(
                target=target,
                iter=iterable,
            ):
                self._loops.append(
                    _Loop(
                        scope=scope,
                        target=target,
                        iterable=iterable,
                    )
                )

    def _state(self, scope: int, spelling: str, annotation: ast.expr) -> None:
        type_name = annotation_type_name(annotation)
        if type_name is not None:
            self._write(scope, spelling, type_name)

    def _read_assignment(
        self,
        scope: int,
        target: ast.expr,
        value: ast.expr,
    ) -> None:
        target_spelling = expression_spelling(target)
        if target_spelling is None:
            return

        match value:
            case ast.Call(func=func):
                constructed = terminal_name(func)
                if constructed is not None:
                    self._write(scope, target_spelling, constructed)
            case ast.Name() | ast.Attribute():
                source_spelling = expression_spelling(value)
                if source_spelling is not None:
                    self._aliases.append(
                        _Alias(
                            scope=scope,
                            target=target_spelling,
                            source=source_spelling,
                        )
                    )

    def _write(self, scope: int, spelling: str, type_name: str) -> None:
        if ATTRIBUTE_SEPARATOR in spelling:
            self._attribute_types[spelling] = type_name
        else:
            self._names[scope][spelling] = type_name

    def _visible(self, scope: int) -> Dict[str, str]:
        chain: List[int] = []
        current: Optional[int] = scope
        while current is not None:
            chain.append(current)
            current = self._parents[current]

        visible = dict(self._attribute_types)
        for enclosing in reversed(chain):
            visible.update(self._names[enclosing])

        return visible

    def _carry_aliases(self) -> None:
        while self._carry_round():
            continue

    def _carry_round(self) -> bool:
        carried = False
        for alias in self._aliases:
            visible = self._visible(alias.scope)
            source_type = visible.get(alias.source)
            if alias.target not in visible and source_type is not None:
                self._write(alias.scope, alias.target, source_type)
                carried = True

        return carried

    def _bind_loops(self) -> None:
        for loop in self._loops:
            container = iterated_container(loop.iterable)
            if container is None:
                continue

            item_types = self._item_types.get(container.spelling)
            if item_types:
                self._bind_loop_target(loop, container.accessor, item_types)

    def _bind_loop_target(
        self,
        loop: _Loop,
        accessor: Optional[str],
        item_types: Tuple[str, ...],
    ) -> None:
        target = loop.target
        if accessor == ITEM_ACCESSOR and isinstance(target, ast.Tuple) and len(target.elts) == ITEM_TARGET_COUNT:
            key_target, value_target = target.elts
            self._bind_name(loop.scope, key_target, item_types[0])
            self._bind_name(loop.scope, value_target, item_types[-1])
            return

        if accessor == VALUE_ACCESSOR:
            self._bind_name(loop.scope, target, item_types[-1])
            return

        self._bind_name(loop.scope, target, item_types[0])

    def _bind_name(self, scope: int, target: ast.expr, type_name: str) -> None:
        spelling = expression_spelling(target)
        if spelling is not None:
            self._write(scope, spelling, type_name)


def module_scopes(
    tree: ast.Module,
    *,
    imported_item_types: Mapping[str, Tuple[str, ...]],
) -> List[Scope]:
    """Reads the types a module states for its names, one entry per lexical scope.

    A parameter annotation, an annotated assignment, and an assignment from a direct construction
    each state a type. An assignment of one spelling to another carries that type along, so an
    object taken as a parameter and kept as `self._manager` is known under both spellings. A `for`
    or comprehension target takes the item type of the container it walks.

    Args:
        tree: Parsed module to read.
        imported_item_types: Item types of containers declared in other modules, keyed by the name
            this module imports them under, as `annotation_item_types` states them. A container
            this module annotates itself is read from the tree.

    Returns:
        List[Scope]: The module scope first, then the scopes it opens, each holding the types
            visible inside it.
    """
    item_types = {**imported_item_types, **container_item_types(tree)}
    reader = _ModuleReader(item_types)
    reader.read(tree, None)
    return reader.scopes()
