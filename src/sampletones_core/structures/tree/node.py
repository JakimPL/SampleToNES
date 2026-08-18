from __future__ import annotations

from pathlib import Path
from typing import Optional

from anytree import Node

from sampletones_core.constants.enums import LibraryGeneratorName
from sampletones_core.library import InstructionLibraryKey
from sampletones_core.reconstructions.converter.paths import ConfigDirectoryFields

from .type import NodeType


class TreeNode(Node):  # type: ignore[misc]
    def __init__(
        self,
        name: str,
        node_type: NodeType,
        parent: Optional[TreeNode] = None,
    ) -> None:
        super().__init__(name, parent=parent)
        self.node_type = node_type

    def copy(self, parent: Optional[TreeNode] = None) -> TreeNode:
        return TreeNode(self.name, node_type=self.node_type, parent=parent)


class FileSystemNode(TreeNode):
    def __init__(
        self,
        name: str,
        node_type: NodeType,
        filepath: Path,
        parent: Optional[TreeNode] = None,
    ) -> None:
        super().__init__(name, node_type=node_type, parent=parent)
        self.filepath = filepath

    def copy(self, parent: Optional[TreeNode] = None) -> FileSystemNode:
        return FileSystemNode(
            self.name,
            filepath=self.filepath,
            node_type=self.node_type,
            parent=parent,
        )


class ConfigNode(FileSystemNode):
    """A filesystem node belonging to a reconstruction configuration, carrying the parsed fields.

    A configuration directory encodes its fields in its name, and both the directory itself and the
    reconstructions inside it are read as belonging to that configuration. Holding the parsed
    :class:`ConfigDirectoryFields` on the node lets every reader — labels, tooltips, fonts — state
    the configuration from the node it already has, whatever the node's own filename says.
    """

    def __init__(
        self,
        name: str,
        node_type: NodeType,
        filepath: Path,
        config: ConfigDirectoryFields,
        parent: Optional[TreeNode] = None,
    ) -> None:
        super().__init__(
            name,
            node_type=node_type,
            filepath=filepath,
            parent=parent,
        )
        self.config = config

    def copy(self, parent: Optional[TreeNode] = None) -> ConfigNode:
        return ConfigNode(
            self.name,
            node_type=self.node_type,
            filepath=self.filepath,
            config=self.config,
            parent=parent,
        )


class LibraryNode(TreeNode):
    def __init__(
        self,
        name: str,
        library_key: InstructionLibraryKey,
        node_type: NodeType = NodeType.LIBRARY,
        parent: Optional[TreeNode] = None,
    ) -> None:
        super().__init__(name, node_type=node_type, parent=parent)
        self.library_key = library_key

    def copy(self, parent: Optional[TreeNode] = None) -> LibraryNode:
        return LibraryNode(
            self.name,
            node_type=self.node_type,
            library_key=self.library_key,
            parent=parent,
        )


class GeneratorNode(TreeNode):
    def __init__(
        self,
        name: str,
        generator_name: LibraryGeneratorName,
        node_type: NodeType = NodeType.GENERATOR,
        parent: Optional[TreeNode] = None,
    ) -> None:
        super().__init__(name, node_type=node_type, parent=parent)
        self.generator_name = generator_name

    def copy(self, parent: Optional[TreeNode] = None) -> GeneratorNode:
        return GeneratorNode(
            self.name,
            node_type=self.node_type,
            generator_name=self.generator_name,
            parent=parent,
        )
