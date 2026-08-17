from sampletones_application.logic.reconstruction.browser.tree.configurations.grouping import (
    organize_top_level_config_directories,
)
from sampletones_application.logic.reconstruction.browser.tree.entries.directory import (
    DirectoryEntry,
    ScanEntry,
)
from sampletones_application.logic.reconstruction.browser.tree.entries.reconstruction import (
    ReconstructionEntry,
)
from sampletones_application.logic.reconstruction.browser.tree.entries.scan import (
    ReconstructionScan,
)
from sampletones_core.structures.tree import (
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

    organize_top_level_config_directories(branch)
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
