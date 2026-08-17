from typing import List, Sequence, Tuple

from sampletones_application.logic.reconstruction.browser.tree.containers import (
    find_or_create_group,
)
from sampletones_application.logic.reconstruction.browser.tree.entries.directory import (
    DirectoryEntry,
)
from sampletones_application.logic.reconstruction.browser.tree.entries.reconstruction import (
    ReconstructionEntry,
)
from sampletones_application.logic.reconstruction.browser.tree.entries.scan import (
    ReconstructionScan,
    ScanEntry,
)
from sampletones_core.configs.display import (
    DISPLAY_SEPARATOR,
    GAMMA_PREFIX,
    format_nes_frequency,
    format_sample_rate,
    format_spectrum_method,
    unique_display_names,
)
from sampletones_core.structures.tree import (
    ConfigNode,
    FileSystemNode,
    NodeType,
    TreeNode,
    create_directory_node,
)


def build_configuration_branch(
    scan: ReconstructionScan,
    *,
    name: str,
    parent: TreeNode,
) -> TreeNode:
    """Builds the branch listing reconstructions by the configuration that produced them.

    The scanned folders appear as they sit on disk, and a top-level configuration directory is then
    lifted under frequency ▶ method groups and named by its generators, so configurations sharing a
    spectrum read side by side. A configuration directory nested inside a plain folder keeps its
    friendly name in place, and a reconstruction outside every configuration directory is listed
    here, this being the branch that follows the disk.
    """
    branch = TreeNode(name, node_type=NodeType.GROUP, parent=parent)
    for entry in scan.entries:
        _append_entry(entry, parent=branch)

    _organize_top_level_config_directories(branch)
    return branch


def _append_entry(entry: ScanEntry, *, parent: TreeNode) -> None:
    match entry:
        case ReconstructionEntry():
            FileSystemNode(
                entry.name,
                node_type=NodeType.FILE,
                filepath=entry.path,
                parent=parent,
            )
        case DirectoryEntry():
            directory_node = create_directory_node(
                entry.path,
                name=entry.name,
                config=entry.config,
                parent=parent,
            )
            for child_entry in entry.entries:
                _append_entry(child_entry, parent=directory_node)


def _organize_top_level_config_directories(branch: TreeNode) -> None:
    """Groups top-level config directories under frequencies/method nodes, leaving other folders flat.

    A config directory moves under ``frequencies`` ▶ ``method`` artificial group nodes and is
    renamed to its generator abbreviation, while any other top-level folder keeps the existing
    flat friendly naming for the config directories nested inside it.
    """
    for child in list(branch.children):
        match child:
            case ConfigNode() if child.node_type == NodeType.DIRECTORY:
                _attach_config_directory_under_groups(child, branch)
            case FileSystemNode() if child.node_type == NodeType.DIRECTORY:
                _assign_directory_display_names(child)

    _disambiguate_generator_siblings(branch)


def _attach_config_directory_under_groups(
    directory_node: ConfigNode,
    branch: TreeNode,
) -> None:
    fields = directory_node.config
    frequencies_name = DISPLAY_SEPARATOR.join(
        [
            format_sample_rate(fields.sr),
            format_nes_frequency(fields.nf),
        ]
    )
    method_name = DISPLAY_SEPARATOR.join(
        [
            format_spectrum_method(fields.sm),
            f"{GAMMA_PREFIX}{fields.tg}",
        ]
    )
    frequencies_node = find_or_create_group(frequencies_name, parent=branch)
    method_node = find_or_create_group(method_name, parent=frequencies_node)

    directory_node.name = fields.gn
    directory_node.parent = method_node


def _disambiguate_generator_siblings(node: TreeNode) -> None:
    """Appends a short config hash to generator directories sharing a name under one method group."""
    if node.node_type == NodeType.GROUP:
        _rename_config_directories(
            [(directory_node, directory_node.config.gn) for directory_node in _config_directory_children(node)]
        )

    for child in node.children:
        _disambiguate_generator_siblings(child)


def _assign_directory_display_names(node: TreeNode) -> None:
    """Renames config-directory nodes to friendly labels, disambiguating colliding siblings.

    Only directories whose names parse as reconstruction config directories are rewritten;
    plain folders keep their on-disk name. The check is scoped per parent because duplicate
    display names among siblings would otherwise collapse to duplicate widget tags downstream.
    """
    _rename_config_directories(
        [(directory_node, directory_node.config.display_name) for directory_node in _config_directory_children(node)]
    )
    for child in node.children:
        _assign_directory_display_names(child)


def _config_directory_children(node: TreeNode) -> List[ConfigNode]:
    return [child for child in node.children if isinstance(child, ConfigNode) and child.node_type == NodeType.DIRECTORY]


def _rename_config_directories(
    proposed_names: Sequence[Tuple[ConfigNode, str]],
) -> None:
    """Names each configuration directory, marking those a sibling would otherwise shadow."""
    labels = unique_display_names([(name, directory_node.config.ch) for directory_node, name in proposed_names])
    for (directory_node, _), label in zip(proposed_names, labels):
        directory_node.name = label
