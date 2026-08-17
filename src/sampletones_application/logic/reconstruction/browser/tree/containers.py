from sampletones_core.structures.tree import NodeType, TreeNode


def find_or_create_group(name: str, *, parent: TreeNode) -> TreeNode:
    """Answers the group of this name under ``parent``, adding one where the parent holds none.

    A group stands for something the disk states rather than holds — a frequency pair, a spectrum
    method, a source folder — so a builder meeting that name again extends the group it already made.
    """
    return _find_or_create(name, node_type=NodeType.GROUP, parent=parent)


def find_or_create_sample(name: str, *, parent: TreeNode) -> TreeNode:
    """Answers the sample of this name under ``parent``, adding one where the parent holds none.

    A sample stands for one source audio and gathers the reconstructions made from it. It carries a
    node type of its own, so a folder and an audio of the same name stay two rows: each is looked up
    among the siblings of its own kind.
    """
    return _find_or_create(name, node_type=NodeType.SAMPLE, parent=parent)


def _find_or_create(
    name: str,
    *,
    node_type: NodeType,
    parent: TreeNode,
) -> TreeNode:
    for child in parent.children:
        if isinstance(child, TreeNode) and child.node_type == node_type and child.name == name:
            return child

    return TreeNode(name, node_type=node_type, parent=parent)
