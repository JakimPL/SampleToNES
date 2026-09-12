from sampletones_application.tags.compose import compose_tag, identity_part
from sampletones_core.structures.tree import TreeNode


def compose_node_tag(node: TreeNode, *, panel_tag: str) -> str:
    """Composes the widget tag of one tree row: readable by the names above it, unique by its path.

    The names read the row back to whoever inspects the widget tree, and the identity part states
    the exact path — each ancestor's node type together with its name — so every row the names
    alone spell alike keeps a tag of its own: a folder and the audio beside it, or two labels
    differing only in spacing or case.
    """
    names = "_".join(str(ancestor.name) for ancestor in node.path)
    return compose_tag(panel_tag, f"node_{names}", _node_identity(node))


def _node_identity(node: TreeNode) -> str:
    return identity_part(
        *(part for ancestor in node.path for part in (ancestor.node_type.value, str(ancestor.name))),
    )
