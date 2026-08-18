from pathlib import Path
from typing import Optional

from sampletones_core.reconstructions.converter.paths import ConfigDirectoryFields

from .node import ConfigNode, FileSystemNode, TreeNode
from .type import NodeType


def create_directory_node(
    directory: Path,
    *,
    name: str,
    config: Optional[ConfigDirectoryFields],
    parent: Optional[TreeNode],
) -> FileSystemNode:
    """Builds the directory node that fits the folder, given the configuration its name states.

    A folder stating a reconstruction configuration becomes a :class:`ConfigNode` carrying those
    fields; a folder stating none becomes a plain :class:`FileSystemNode`. The caller states the
    fields it read with :meth:`ConfigDirectoryFields.from_directory_name`, so a caller that already
    read them — a scan of a reconstructions directory — reads each folder name once, and the choice
    of node class stays here.
    """
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
