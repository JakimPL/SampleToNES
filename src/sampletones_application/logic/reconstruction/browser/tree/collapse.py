from sampletones_application.logic.reconstruction.browser.tree.containers import (
    ARTIFICIAL_CONTAINERS,
)
from sampletones_core.configs.display import DISPLAY_SEPARATOR
from sampletones_core.structures.tree import NodeType, TreeNode


def collapse_single_child_containers(node: TreeNode) -> None:
    """Folds every heading the browser invents that stands above a single row into that row.

    A heading leading to one row asks the reader to open a level that tells them nothing new, so the
    row takes the heading's name ahead of its own and rises into its place. Working from the deepest
    rows upwards folds a whole chain at once, one separator per level: with a single configuration
    present the configuration branch reads ``44.1 kHz·30 Hz·FFT·γ0·PTN`` as one row, and it grows back
    into groups as soon as a second configuration arrives.

    The row that survives keeps its node type, its path, its configuration and its children, so its
    click behaviour, theme, context menu and favorite star carry over from before the fold. The two
    branch roots stay in place, since each names a way of reading the whole tree, and a folder the disk
    holds stays a folder of its own, since the configuration branch mirrors the disk.
    """
    for child in list(node.children):
        collapse_single_child_containers(child)

    if _can_fold(node):
        _fold_into_child(node)


def _can_fold(node: TreeNode) -> bool:
    parent = node.parent
    if parent is None or parent.node_type == NodeType.ROOT:
        return False

    if node.node_type not in ARTIFICIAL_CONTAINERS or len(node.children) != 1:
        return False

    return not _siblings_hold(node, _joined_name(node, node.children[0]))


def _siblings_hold(node: TreeNode, name: str) -> bool:
    """Whether a row beside this heading already reads as the name the fold would produce.

    The folded row joins the siblings of the heading it replaces, and a browser row is addressed by
    the names leading to it, so a heading whose fold would repeat a name beside it stays as it is.
    """
    return any(sibling.name == name for sibling in node.parent.children if sibling is not node)


def _fold_into_child(node: TreeNode) -> None:
    child = node.children[0]
    child.name = _joined_name(node, child)
    child.parent = node.parent
    node.parent = None


def _joined_name(node: TreeNode, child: TreeNode) -> str:
    return DISPLAY_SEPARATOR.join([str(node.name), str(child.name)])
