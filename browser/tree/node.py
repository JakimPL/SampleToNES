from pathlib import Path
from typing import Any, Optional

from anytree import Node

from constants.enums import GeneratorClassName, LibraryGeneratorName
from instructions.instruction import Instruction
from library.data import LibraryFragment
from library.key import LibraryKey


class TreeNode(Node):
    def __init__(
        self,
        name: str,
        node_type: str,
        parent: Optional["TreeNode"] = None,
    ) -> None:
        super().__init__(name, parent=parent)
        self.node_type = node_type

    def copy(self, parent: Optional["TreeNode"] = None) -> "TreeNode":
        return TreeNode(self.name, node_type=self.node_type, parent=parent)


class FileSystemNode(TreeNode):
    def __init__(
        self,
        name: str,
        node_type: str,
        filepath: Path,
        parent: Optional[TreeNode] = None,
    ) -> None:
        super().__init__(name, node_type=node_type, parent=parent)
        self.filepath = filepath

    def copy(self, parent: Optional[TreeNode] = None) -> "FileSystemNode":
        return FileSystemNode(self.name, filepath=self.filepath, node_type=self.node_type, parent=parent)


class LibraryNode(TreeNode):
    def __init__(
        self,
        name: str,
        node_type: str,
        library_key: LibraryKey,
        parent: Optional[TreeNode] = None,
    ) -> None:
        super().__init__(name, node_type=node_type, parent=parent)
        self.library_key = library_key

    def copy(self, parent: Optional[TreeNode] = None) -> "LibraryNode":
        return LibraryNode(self.name, node_type=self.node_type, library_key=self.library_key, parent=parent)


class GeneratorNode(TreeNode):
    def __init__(
        self,
        name: str,
        node_type: str,
        generator_name: LibraryGeneratorName,
        parent: Optional[TreeNode] = None,
    ) -> None:
        super().__init__(name, node_type=node_type, parent=parent)
        self.generator_name = generator_name

    def copy(self, parent: Optional[TreeNode] = None) -> "GeneratorNode":
        return GeneratorNode(
            self.name,
            node_type=self.node_type,
            generator_name=self.generator_name,
            parent=parent,
        )


class GroupNode(TreeNode):
    def __init__(
        self,
        name: str,
        node_type: str,
        generator_name: LibraryGeneratorName,
        group_key: str,
        parent: Optional[TreeNode] = None,
    ) -> None:
        super().__init__(name, node_type=node_type, parent=parent)
        self.generator_name = generator_name
        self.group_key = group_key

    def copy(self, parent: Optional[TreeNode] = None) -> "GroupNode":
        return GroupNode(
            self.name,
            node_type=self.node_type,
            generator_name=self.generator_name,
            group_key=self.group_key,
            parent=parent,
        )


class InstructionNode(TreeNode):
    def __init__(
        self,
        name: str,
        node_type: str,
        generator_name: LibraryGeneratorName,
        generator_class_name: GeneratorClassName,
        instruction: Instruction,
        fragment: LibraryFragment,
        parent: Optional[TreeNode] = None,
    ) -> None:
        super().__init__(name, node_type=node_type, parent=parent)
        self.generator_name = generator_name
        self.generator_class_name = generator_class_name
        self.instruction = instruction
        self.fragment = fragment

    def copy(self, parent: Optional[TreeNode] = None) -> "InstructionNode":
        return InstructionNode(
            self.name,
            node_type=self.node_type,
            generator_name=self.generator_name,
            generator_class_name=self.generator_class_name,
            instruction=self.instruction,
            fragment=self.fragment,
            parent=parent,
        )
