from dataclasses import dataclass
from typing import FrozenSet, Iterable

from .node import TreeNode


@dataclass(frozen=True)
class TreeVisibility:
    """The rows a criterion keeps on screen, held as the rows it named and the rows standing above them.

    A named row stays, and so do the rows leading down to it and the rows it holds: a named file is
    read under the folders it sits in, and a named folder shows what it gathers. Keeping the named
    rows and their ancestors alone holds the memory to the size of what was found, and a row below a
    match is answered from its own path upwards.
    """

    matches: FrozenSet[TreeNode]
    ancestors: FrozenSet[TreeNode]

    def is_visible(self, node: TreeNode) -> bool:
        """Whether the row stays on screen: it was named, it leads to a named row, or one holds it."""
        if node in self.matches or node in self.ancestors:
            return True

        return any(ancestor in self.matches for ancestor in node.ancestors)

    def should_expand(self, node: TreeNode) -> bool:
        """Whether the row stands open, which a named row does and so does every row above one."""
        return node in self.matches or node in self.ancestors

    def leads_to(self, node: TreeNode) -> bool:
        """Whether the row stands on the way down to a named row, being none of the named rows itself.

        Answers the reader who is pointed at what was named rather than at what it holds, so opening
        by this leaves a named row standing as it was while the rows above it show where it sits.
        """
        return node in self.ancestors


def resolve_visibility(matches: Iterable[TreeNode]) -> TreeVisibility:
    """The visibility a set of named rows resolves to, read once per pass over the tree.

    Args:
        matches: The rows a criterion named, in any order.
    """
    matched = frozenset(matches)
    return TreeVisibility(
        matches=matched,
        ancestors=frozenset(ancestor for node in matched for ancestor in node.ancestors),
    )
