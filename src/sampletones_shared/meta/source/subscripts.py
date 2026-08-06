import ast
from dataclasses import dataclass
from typing import Collection, List, Tuple

from sampletones_shared.meta.source.nodes import expression_spelling, own_nodes, slice_elements


@dataclass(frozen=True)
class SubscriptSite:
    """One subscript a module writes on an expression whose type is known."""

    receiver: str
    node: ast.Subscript

    @property
    def parts(self) -> Tuple[ast.expr, ...]:
        """The expressions the brackets hold, one per comma-separated part."""
        return slice_elements(self.node)

    @property
    def line(self) -> int:
        return self.node.lineno


def find_subscripts(
    scope: ast.AST,
    receivers: Collection[str],
) -> List[SubscriptSite]:
    """Every subscript a scope's own region writes on one of the given spellings.

    A nested function is a scope of its own, so its subscripts are found by searching it in turn.

    Args:
        scope: Module, function, or lambda to search.
        receivers: Spellings that hold the type of interest, as `TypeEnvironment.spellings_of`
            states them.

    Returns:
        List[SubscriptSite]: The sites, in source order.
    """
    sites: List[SubscriptSite] = []
    for node in own_nodes(scope):
        if not isinstance(node, ast.Subscript):
            continue

        receiver = expression_spelling(node.value)
        if receiver is not None and receiver in receivers:
            sites.append(
                SubscriptSite(
                    receiver=receiver,
                    node=node,
                )
            )

    return sorted(
        sites,
        key=lambda site: (
            site.node.lineno,
            site.node.col_offset,
        ),
    )
