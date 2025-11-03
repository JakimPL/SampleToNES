from pathlib import Path
from typing import Any, Optional

from anytree import Node


class TreeNode(Node):
    def __init__(self, name: str, parent: Optional["TreeNode"] = None, node_type: Optional[str] = None) -> None:
        super().__init__(name, parent=parent)
        self.node_type = node_type

    def copy(self, parent: Optional["TreeNode"] = None) -> "TreeNode":
        return TreeNode(self.name, parent=parent, node_type=self.node_type)


class FileSystemNode(TreeNode):
    def __init__(
        self,
        name: str,
        parent: Optional[TreeNode] = None,
        node_type: Optional[str] = None,
        file_path: Optional[Path] = None,
    ) -> None:
        super().__init__(name, parent=parent, node_type=node_type)
        self.file_path = file_path

    def copy(self, parent: Optional[TreeNode] = None) -> "FileSystemNode":
        return FileSystemNode(self.name, parent=parent, node_type=self.node_type, file_path=self.file_path)


class LibraryNode(TreeNode):
    def __init__(
        self,
        name: str,
        parent: Optional[TreeNode] = None,
        node_type: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> None:
        super().__init__(name, parent=parent, node_type=node_type)
        self.display_name = display_name

    def copy(self, parent: Optional[TreeNode] = None) -> "LibraryNode":
        return LibraryNode(self.name, parent=parent, node_type=self.node_type, display_name=self.display_name)


class GeneratorNode(TreeNode):
    def __init__(
        self,
        name: str,
        parent: Optional[TreeNode] = None,
        node_type: Optional[str] = None,
        display_name: Optional[str] = None,
        generator_name: Optional[Any] = None,
    ) -> None:
        super().__init__(name, parent=parent, node_type=node_type)
        self.display_name = display_name
        self.generator_name = generator_name

    def copy(self, parent: Optional[TreeNode] = None) -> "GeneratorNode":
        return GeneratorNode(
            self.name,
            parent=parent,
            node_type=self.node_type,
            display_name=self.display_name,
            generator_name=self.generator_name,
        )


class GroupNode(TreeNode):
    def __init__(
        self,
        name: str,
        parent: Optional[TreeNode] = None,
        node_type: Optional[str] = None,
        display_name: Optional[str] = None,
        generator_name: Optional[Any] = None,
        group_key: Optional[str] = None,
    ) -> None:
        super().__init__(name, parent=parent, node_type=node_type)
        self.display_name = display_name
        self.generator_name = generator_name
        self.group_key = group_key

    def copy(self, parent: Optional[TreeNode] = None) -> "GroupNode":
        return GroupNode(
            self.name,
            parent=parent,
            node_type=self.node_type,
            display_name=self.display_name,
            generator_name=self.generator_name,
            group_key=self.group_key,
        )


class InstructionNode(TreeNode):
    def __init__(
        self,
        name: str,
        parent: Optional[TreeNode] = None,
        node_type: Optional[str] = None,
        display_name: Optional[str] = None,
        generator_name: Optional[Any] = None,
        generator_class_name: Optional[str] = None,
        instruction: Optional[Any] = None,
        fragment: Optional[Any] = None,
    ) -> None:
        super().__init__(name, parent=parent, node_type=node_type)
        self.display_name = display_name
        self.generator_name = generator_name
        self.generator_class_name = generator_class_name
        self.instruction = instruction
        self.fragment = fragment

    def copy(self, parent: Optional[TreeNode] = None) -> "InstructionNode":
        return InstructionNode(
            self.name,
            parent=parent,
            node_type=self.node_type,
            display_name=self.display_name,
            generator_name=self.generator_name,
            generator_class_name=self.generator_class_name,
            instruction=self.instruction,
            fragment=self.fragment,
        )
