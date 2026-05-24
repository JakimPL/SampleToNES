from __future__ import annotations

from pathlib import Path
from typing import Optional

from anytree import Node

from sampletones_core.constants.enums import LibraryGeneratorName
from sampletones_core.library import InstructionLibraryKey

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
        return FileSystemNode(self.name, filepath=self.filepath, node_type=self.node_type, parent=parent)


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
        return LibraryNode(self.name, node_type=self.node_type, library_key=self.library_key, parent=parent)


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
