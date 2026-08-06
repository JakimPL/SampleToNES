import ast
from dataclasses import dataclass
from typing import Final, FrozenSet, Mapping, Tuple

from sampletones_shared.meta.source.bindings.environment import TypeEnvironment
from sampletones_shared.meta.source.nodes import expression_spelling, terminal_name

EnumMembers = Mapping[str, str]
EnumTable = Mapping[str, EnumMembers]


@dataclass(frozen=True)
class ResolvedValues:
    """The strings an expression can spell, and whether the source writes each of them.

    An exact resolution draws every value from a literal the source writes, so a caller may hold
    the code to precisely these values. A resolution over an enum's members is inexact: it covers
    every value the site can reach, which serves a caller asking which values are reachable at all.
    An empty resolution states that the expression stays out of reach of this analysis.
    """

    values: Tuple[str, ...]
    exact: bool

    @property
    def resolved(self) -> bool:
        return bool(self.values)


UNRESOLVED: Final[ResolvedValues] = ResolvedValues(values=(), exact=False)


@dataclass(frozen=True)
class ValueResolver:
    """Resolves an expression to the strings it can spell, from one module's view of its names.

    A string literal and an enum member each resolve to themselves. A conditional resolves to both
    of its branches. An enum call, and a name the module states to hold an enum, resolve to every
    member of that enum. A name bound to a module constant resolves to whatever that constant's
    value resolves to.
    """

    environment: TypeEnvironment
    enums: EnumTable
    constants: Mapping[str, ast.expr]

    def resolve(self, node: ast.expr) -> ResolvedValues:
        """Resolves one expression.

        Args:
            node: Expression to resolve.

        Returns:
            ResolvedValues: The values the expression can spell, empty where it stays out of reach.
        """
        return self._resolve(node, frozenset())

    def _resolve(self, node: ast.expr, visited: FrozenSet[str]) -> ResolvedValues:
        match node:
            case ast.Constant(value=str() as text):
                return ResolvedValues(values=(text,), exact=True)
            case ast.Attribute(value=ast.Name(id=owner), attr=member) if owner in self.enums:
                return self._member(owner, member)
            case ast.IfExp(body=body, orelse=orelse):
                return self._merged(
                    self._resolve(body, visited),
                    self._resolve(orelse, visited),
                )
            case ast.Call(func=func):
                return self._called_enum(func)
            case ast.Name() | ast.Attribute():
                return self._spelled(node, visited)
            case _:
                return UNRESOLVED

    @staticmethod
    def _merged(first: ResolvedValues, second: ResolvedValues) -> ResolvedValues:
        if not (first.resolved and second.resolved):
            return UNRESOLVED

        return ResolvedValues(
            values=tuple(dict.fromkeys(first.values + second.values)),
            exact=first.exact and second.exact,
        )

    def _member(self, owner: str, member: str) -> ResolvedValues:
        value = self.enums[owner].get(member)
        if value is None:
            return UNRESOLVED

        return ResolvedValues(values=(value,), exact=True)

    def _members(self, enum_name: str) -> ResolvedValues:
        members = self.enums.get(enum_name)
        if members is None:
            return UNRESOLVED

        return ResolvedValues(values=tuple(members.values()), exact=False)

    def _called_enum(self, func: ast.expr) -> ResolvedValues:
        called = terminal_name(func)
        if called is None:
            return UNRESOLVED

        return self._members(called)

    def _spelled(
        self,
        node: ast.expr,
        visited: FrozenSet[str],
    ) -> ResolvedValues:
        spelling = expression_spelling(node)
        if spelling is None:
            return UNRESOLVED

        type_name = self.environment.type_of(spelling)
        if type_name is not None and type_name in self.enums:
            return self._members(type_name)

        value = self.constants.get(spelling)
        if value is None or spelling in visited:
            return UNRESOLVED

        return self._resolve(value, visited | {spelling})
