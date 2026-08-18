from sampletones_application.logic.reconstruction.browser.tree.containers import (
    ARTIFICIAL_CONTAINERS,
)
from sampletones_core.structures.tree import TreeNode


def prune_empty_containers(node: TreeNode) -> None:
    """Drops the containers the browser invents that gather nothing, deepest first.

    A group or a sample is a heading the browser writes itself, so one left holding nothing says
    nothing and leaves. Working from the deepest rows upwards lets a whole chain of such headings go
    at once, the branch root among them, which keeps a reconstructions directory holding nothing to
    show silent. A folder the disk holds stays where it is, since the configuration branch reads the
    disk as it is.
    """
    for child in list(node.children):
        prune_empty_containers(child)

    if node.node_type in ARTIFICIAL_CONTAINERS and not node.children and node.parent is not None:
        node.parent = None
