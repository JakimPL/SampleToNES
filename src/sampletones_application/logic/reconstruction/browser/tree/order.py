from typing import Tuple

from sampletones_core.structures.tree import NodeType, TreeNode
from sampletones_shared.utils.text import NaturalSortKey, natural_sort_key


def order_children(node: TreeNode) -> None:
    """Sorts every set of siblings into reading order: what opens first, then names read naturally.

    The pass runs once every label is final, so a row sits where its displayed name puts it — `8 kHz`
    ahead of `44.1 kHz`, whatever the folder names on disk spell. The branches directly under the
    container root keep the order the browser states them in.
    """
    for child in node.children:
        order_children(child)

    if node.node_type != NodeType.ROOT:
        node.children = tuple(sorted(node.children, key=_sibling_key))


def _sibling_key(node: TreeNode) -> Tuple[bool, NaturalSortKey]:
    return (
        node.node_type == NodeType.FILE,
        natural_sort_key(str(node.name)),
    )
