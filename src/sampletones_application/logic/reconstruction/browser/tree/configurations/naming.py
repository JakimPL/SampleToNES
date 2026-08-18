from typing import List, Sequence, Tuple

from sampletones_core.configs.display import unique_display_names
from sampletones_core.structures.tree import ConfigNode, NodeType, TreeNode


def disambiguate_generator_siblings(node: TreeNode) -> None:
    """Appends a short config hash to generator directories sharing a name under one method group."""
    if node.node_type == NodeType.GROUP:
        _rename_config_directories(
            [(directory_node, directory_node.config.gn) for directory_node in _config_directory_children(node)]
        )

    for child in node.children:
        disambiguate_generator_siblings(child)


def assign_display_names(node: TreeNode) -> None:
    """Renames config-directory nodes to friendly labels, disambiguating colliding siblings.

    Only directories whose names parse as reconstruction config directories are rewritten;
    plain folders keep their on-disk name. The check is scoped per parent because duplicate
    display names among siblings would otherwise collapse to duplicate widget tags downstream.
    """
    _rename_config_directories(
        [(directory_node, directory_node.config.display_name) for directory_node in _config_directory_children(node)]
    )
    for child in node.children:
        assign_display_names(child)


def _config_directory_children(node: TreeNode) -> List[ConfigNode]:
    return [child for child in node.children if isinstance(child, ConfigNode) and child.node_type == NodeType.DIRECTORY]


def _rename_config_directories(
    proposed_names: Sequence[Tuple[ConfigNode, str]],
) -> None:
    """Names each configuration directory, marking those a sibling would otherwise shadow."""
    labels = unique_display_names([(name, directory_node.config.ch) for directory_node, name in proposed_names])
    for (directory_node, _), label in zip(proposed_names, labels):
        directory_node.name = label
