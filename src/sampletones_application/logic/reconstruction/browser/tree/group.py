from sampletones_core.structures.tree import NodeType, TreeNode


def find_or_create_group(name: str, *, parent: TreeNode) -> TreeNode:
    """Answers the group of this name under ``parent``, adding one where the parent holds none.

    A group stands for something the disk states rather than holds — a frequency pair, a spectrum
    method, a source folder — so it is identified by its name and a builder meeting that name again
    extends the group it already made.
    """
    for child in parent.children:
        if isinstance(child, TreeNode) and child.node_type == NodeType.GROUP and child.name == name:
            return child

    return TreeNode(name, node_type=NodeType.GROUP, parent=parent)
