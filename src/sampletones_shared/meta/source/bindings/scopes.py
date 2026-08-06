import ast
from dataclasses import dataclass
from typing import Dict, List, NamedTuple, Optional

from sampletones_shared.meta.source.bindings.containers import (
    ItemTypes,
    container_item_types,
    iterated_container,
    iterated_types,
)
from sampletones_shared.meta.source.bindings.environment import TypeEnvironment
from sampletones_shared.meta.source.bindings.statements import (
    AliasStatement,
    LoopStatement,
    Statement,
    TypeStatement,
    read_statement,
)
from sampletones_shared.meta.source.nodes import expression_spelling, is_attribute_spelling, nested_scopes, own_nodes


@dataclass(frozen=True)
class Scope:
    """One lexical scope of a module — the module itself, a function, or a lambda."""

    node: ast.AST
    environment: TypeEnvironment


class _ScopedAlias(NamedTuple):
    scope: int
    statement: AliasStatement


class _ScopedLoop(NamedTuple):
    scope: int
    statement: LoopStatement


class _ScopeReader:
    """Collects what a module's statements say, scope by scope, and resolves the result.

    A bare name belongs to the scope that declares it, so two methods may each take an `element`
    parameter of their own type. An attribute chain such as `self._manager` belongs to the module,
    which is what lets one method state the type another method reads.
    """

    def __init__(self, item_types: ItemTypes) -> None:
        self._item_types: ItemTypes = item_types
        self._attribute_types: Dict[str, str] = {}
        self._nodes: List[ast.AST] = []
        self._parents: List[Optional[int]] = []
        self._names: List[Dict[str, str]] = []
        self._aliases: List[_ScopedAlias] = []
        self._loops: List[_ScopedLoop] = []

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
            self._collect(scope, read_statement(owned))

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

    def _collect(self, scope: int, statement: Optional[Statement]) -> None:
        match statement:
            case TypeStatement(spelling=spelling, type_name=type_name):
                self._write(scope, spelling, type_name)
            case AliasStatement():
                self._aliases.append(
                    _ScopedAlias(
                        scope=scope,
                        statement=statement,
                    )
                )
            case LoopStatement():
                self._loops.append(
                    _ScopedLoop(
                        scope=scope,
                        statement=statement,
                    )
                )

    def _write(self, scope: int, spelling: str, type_name: str) -> None:
        if is_attribute_spelling(spelling):
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
        for scope, alias in self._aliases:
            visible = self._visible(scope)
            source_type = visible.get(alias.source)
            if alias.target not in visible and source_type is not None:
                self._write(scope, alias.target, source_type)
                carried = True

        return carried

    def _bind_loops(self) -> None:
        for scope, loop in self._loops:
            container = iterated_container(loop.iterable)
            if container is None:
                continue

            item_types = self._item_types.get(container.spelling, ())
            for target, type_name in iterated_types(loop.target, container.accessor, item_types):
                self._bind(scope, target, type_name)

    def _bind(self, scope: int, target: ast.expr, type_name: str) -> None:
        spelling = expression_spelling(target)
        if spelling is not None:
            self._write(scope, spelling, type_name)


def module_scopes(
    tree: ast.Module,
    *,
    imported_item_types: ItemTypes,
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
    reader = _ScopeReader({**imported_item_types, **container_item_types(tree)})
    reader.read(tree, None)
    return reader.scopes()
