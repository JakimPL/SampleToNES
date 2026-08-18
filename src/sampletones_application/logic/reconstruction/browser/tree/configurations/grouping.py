from sampletones_application.logic.reconstruction.browser.tree.configurations.naming import (
    assign_display_names,
    disambiguate_generator_siblings,
)
from sampletones_application.logic.reconstruction.browser.tree.containers import (
    find_or_create_config_group,
)
from sampletones_core.configs.display import (
    format_frequencies,
    format_transformation,
)
from sampletones_core.structures.tree import (
    ConfigNode,
    FileSystemNode,
    NodeType,
    TreeNode,
)


def organize_top_level_config_directories(branch: TreeNode) -> None:
    """Groups top-level config directories under frequencies/transformation nodes, leaving other folders flat.

    A config directory moves under ``frequencies`` ▶ ``transformation`` configuration headings and is
    renamed to its generator abbreviation, so the three rows leading to it spell its display name.
    Any other top-level folder keeps the flat friendly naming for the config directories nested
    inside it.
    """
    for child in list(branch.children):
        match child:
            case ConfigNode() if child.node_type == NodeType.DIRECTORY:
                _attach_config_directory_under_groups(child, branch)
            case FileSystemNode() if child.node_type == NodeType.DIRECTORY:
                assign_display_names(child)

    disambiguate_generator_siblings(branch)


def _attach_config_directory_under_groups(
    directory_node: ConfigNode,
    branch: TreeNode,
) -> None:
    fields = directory_node.config
    frequencies_node = find_or_create_config_group(
        format_frequencies(fields.sr, fields.nf),
        parent=branch,
    )
    transformation_node = find_or_create_config_group(
        format_transformation(fields.sm, fields.tg),
        parent=frequencies_node,
    )

    directory_node.name = fields.gn
    directory_node.parent = transformation_node
