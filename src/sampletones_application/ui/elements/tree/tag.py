from typing import Final

from sampletones_application.tags.compose import compose_tag
from sampletones_core.structures.tree import TreeNode
from sampletones_shared.utils.serialization import calculate_hash

NODE_TAG_DIGEST_LENGTH: Final[int] = 8

_IDENTITY_SEPARATOR: Final[str] = "\x00"


def compose_node_tag(node: TreeNode, *, panel_tag: str) -> str:
    """Composes the widget tag of one tree row: readable by the names above it, unique by its path.

    The names read the row back to whoever inspects the widget tree, and the digest states the exact
    path — each ancestor's node type together with its name — so every row the names alone spell
    alike keeps a tag of its own: a folder and the audio beside it, or two labels differing only in
    spacing or case. The separator the digest joins on is one the disk gives no name, which is what
    makes one identity reach one digest.
    """
    names = "_".join(str(ancestor.name) for ancestor in node.path)
    return compose_tag(panel_tag, f"node_{names}", _node_digest(node))


def _node_digest(node: TreeNode) -> str:
    identity = _IDENTITY_SEPARATOR.join(
        part for ancestor in node.path for part in (ancestor.node_type.value, str(ancestor.name))
    )
    return calculate_hash(identity, length=NODE_TAG_DIGEST_LENGTH)
