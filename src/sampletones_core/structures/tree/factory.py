from pathlib import Path
from typing import Optional

from sampletones_core.reconstructions.converter.paths import ConfigDirectoryFields

from .node import ConfigNode, FileSystemNode, TreeNode
from .type import NodeType


def create_directory_node(
    directory: Path,
    *,
    name: str,
    parent: Optional[TreeNode],
) -> FileSystemNode:
    """Builds the directory node that fits the folder, reading its configuration where it names one.

    A folder whose name parses as a reconstruction configuration directory becomes a
    :class:`ConfigNode` carrying those fields; every other folder becomes a plain
    :class:`FileSystemNode`. Routing every directory through here keeps the decision of which node
    class carries a configuration in one place.
    """
    config = ConfigDirectoryFields.from_directory_name(directory.name)
    if config is None:
        return FileSystemNode(
            name,
            node_type=NodeType.DIRECTORY,
            filepath=directory,
            parent=parent,
        )

    return ConfigNode(
        name,
        node_type=NodeType.DIRECTORY,
        filepath=directory,
        config=config,
        parent=parent,
    )
