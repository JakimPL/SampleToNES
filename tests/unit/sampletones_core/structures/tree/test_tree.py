from pathlib import Path
from typing import Final, List

import pytest

from sampletones_core.structures.tree.node import FileSystemNode, TreeNode
from sampletones_core.structures.tree.tree import Tree
from sampletones_core.structures.tree.type import NodeType

SONG_PATH: Final[Path] = Path("/reconstructions/song.stn")


@pytest.fixture
def all_nodes() -> List[TreeNode]:
    root = TreeNode("root", NodeType.ROOT)
    child_a = TreeNode("child_a", NodeType.DIRECTORY, parent=root)
    child_b = TreeNode("child_b", NodeType.DIRECTORY, parent=root)
    leaf_aa = TreeNode("leaf_aa", NodeType.FILE, parent=child_a)
    leaf_ab = TreeNode("leaf_ab", NodeType.FILE, parent=child_a)
    leaf_ba = TreeNode("leaf_ba", NodeType.FILE, parent=child_b)
    return [root, child_a, child_b, leaf_aa, leaf_ab, leaf_ba]


@pytest.fixture
def tree(all_nodes: List[TreeNode]) -> Tree:
    return Tree(root=all_nodes[0])


class TestTreeRootManagement:
    def test_empty_tree_root_is_none(self) -> None:
        assert Tree().root is None

    def test_set_root_stores_root(self, all_nodes: List[TreeNode]) -> None:
        t = Tree()
        t.set_root(all_nodes[0])
        assert t.root is all_nodes[0]

    def test_get_root_returns_root(
        self,
        all_nodes: List[TreeNode],
        tree: Tree,
    ) -> None:
        assert tree.get_root() is all_nodes[0]

    def test_set_root_replaces_the_shape(self, tree: Tree) -> None:
        replacement = TreeNode("replacement", NodeType.ROOT)
        tree.set_root(replacement)
        assert tree.get_root() is replacement


class TestTreeFindNodes:
    @staticmethod
    def _tree_with_twins() -> Tree:
        root = TreeNode("root", NodeType.ROOT)
        by_configuration = TreeNode("by_configuration", NodeType.GROUP, parent=root)
        by_sample = TreeNode("by_sample", NodeType.GROUP, parent=root)
        FileSystemNode("song", NodeType.FILE, SONG_PATH, parent=by_configuration)
        FileSystemNode("44.1 kHz", NodeType.FILE, SONG_PATH, parent=by_sample)
        FileSystemNode("other", NodeType.FILE, Path("/reconstructions/other.stn"), parent=by_sample)
        return Tree(root=root)

    def test_empty_tree_answers_nothing(self) -> None:
        assert Tree().find_nodes(TreeNode, lambda node: True) == ()

    def test_every_node_standing_for_one_path_is_answered(self) -> None:
        tree = self._tree_with_twins()
        twins = tree.find_nodes(FileSystemNode, lambda node: node.filepath == SONG_PATH)
        assert [twin.name for twin in twins] == ["song", "44.1 kHz"]

    def test_nodes_of_other_classes_stay_out(self) -> None:
        tree = self._tree_with_twins()
        assert all(isinstance(node, FileSystemNode) for node in tree.find_nodes(FileSystemNode, lambda node: True))

    def test_the_answer_reads_in_tree_order(self, tree: Tree) -> None:
        found = tree.find_nodes(TreeNode, lambda node: node.node_type == NodeType.FILE)
        assert [node.name for node in found] == ["leaf_aa", "leaf_ab", "leaf_ba"]

    def test_a_predicate_nothing_answers_gives_nothing(self, tree: Tree) -> None:
        assert tree.find_nodes(FileSystemNode, lambda node: True) == ()
