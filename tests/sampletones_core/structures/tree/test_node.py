from pathlib import Path

from sampletones_core.configs import Config
from sampletones_core.constants.enums import LibraryGeneratorName
from sampletones_core.library import InstructionLibraryKey
from sampletones_core.structures.tree.node import (
    FileSystemNode,
    GeneratorNode,
    LibraryNode,
    TreeNode,
)
from sampletones_core.structures.tree.type import NodeType

LIBRARY_KEY = InstructionLibraryKey.from_config(Config())


class TestTreeNode:
    def test_standalone_node_has_no_parent(self) -> None:
        node = TreeNode("root", NodeType.ROOT)
        assert node.parent is None

    def test_node_type_is_stored(self) -> None:
        node = TreeNode("n", NodeType.FILE)
        assert node.node_type == NodeType.FILE

    def test_child_node_parent_is_set(self) -> None:
        parent = TreeNode("parent", NodeType.ROOT)
        child = TreeNode("child", NodeType.FILE, parent=parent)
        assert child.parent is parent

    def test_copy_preserves_name_and_type(self) -> None:
        node = TreeNode("original", NodeType.DIRECTORY)
        copied = node.copy()
        assert copied.name == "original"
        assert copied.node_type == NodeType.DIRECTORY

    def test_copy_with_parent_attaches_to_parent(self) -> None:
        root = TreeNode("root", NodeType.ROOT)
        node = TreeNode("n", NodeType.FILE)
        copied = node.copy(parent=root)
        assert copied.parent is root

    def test_copy_without_parent_creates_orphan(self) -> None:
        parent = TreeNode("parent", NodeType.ROOT)
        node = TreeNode("child", NodeType.FILE, parent=parent)
        copied = node.copy()
        assert copied.parent is None


class TestFileSystemNode:
    def test_filepath_is_stored(self) -> None:
        path = Path("/some/file.wav")
        node = FileSystemNode("f", NodeType.FILE, filepath=path)
        assert node.filepath == path

    def test_copy_preserves_filepath_and_type(self) -> None:
        path = Path("/some/file.wav")
        node = FileSystemNode("f", NodeType.FILE, filepath=path)
        copied = node.copy()
        assert copied.filepath == path
        assert copied.node_type == NodeType.FILE


class TestLibraryNode:
    def test_library_key_is_stored(self) -> None:
        node = LibraryNode("lib", library_key=LIBRARY_KEY)
        assert node.library_key == LIBRARY_KEY

    def test_copy_preserves_library_key(self) -> None:
        node = LibraryNode("lib", library_key=LIBRARY_KEY)
        copied = node.copy()
        assert copied.library_key == LIBRARY_KEY

    def test_default_node_type_is_library(self) -> None:
        node = LibraryNode("lib", library_key=LIBRARY_KEY)
        assert node.node_type == NodeType.LIBRARY


class TestGeneratorNode:
    def test_generator_name_is_stored(self) -> None:
        node = GeneratorNode("gen", generator_name=LibraryGeneratorName.PULSE)
        assert node.generator_name == LibraryGeneratorName.PULSE

    def test_copy_preserves_generator_name(self) -> None:
        node = GeneratorNode("gen", generator_name=LibraryGeneratorName.PULSE)
        copied = node.copy()
        assert copied.generator_name == LibraryGeneratorName.PULSE

    def test_default_node_type_is_generator(self) -> None:
        node = GeneratorNode("gen", generator_name=LibraryGeneratorName.PULSE)
        assert node.node_type == NodeType.GENERATOR
