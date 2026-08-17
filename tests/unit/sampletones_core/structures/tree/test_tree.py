from dataclasses import dataclass
from pathlib import Path
from typing import Final, List

import pytest

from sampletones_core.structures.tree.node import FileSystemNode, TreeNode
from sampletones_core.structures.tree.tree import Tree
from sampletones_core.structures.tree.type import NodeType
from tests.suite.case import BaseTestCase

SONG_PATH: Final[Path] = Path("/reconstructions/song.stn")


def name_predicate(node: TreeNode, query: str) -> bool:
    return query in node.name


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

    def test_set_root_clears_existing_filter(
        self,
        all_nodes: List[TreeNode],
        tree: Tree,
    ) -> None:
        tree.apply_filter("child_a", name_predicate)
        assert tree.is_filtered()
        tree.set_root(all_nodes[0])
        assert not tree.is_filtered()


class TestTreeFilter:
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseTestCase):
        label: str
        query: str
        expected_visible_names: frozenset[str]
        expected_hidden_names: frozenset[str]

    test_cases = (
        TestCase(
            label="match_leaf",
            query="leaf_ba",
            expected_visible_names=frozenset({"root", "child_b", "leaf_ba"}),
            expected_hidden_names=frozenset({"child_a", "leaf_aa", "leaf_ab"}),
        ),
        TestCase(
            label="match_internal",
            query="child_a",
            expected_visible_names=frozenset(
                {
                    "root",
                    "child_a",
                    "leaf_aa",
                    "leaf_ab",
                }
            ),
            expected_hidden_names=frozenset({"child_b", "leaf_ba"}),
        ),
        TestCase(
            label="no_match",
            query="xyz",
            expected_visible_names=frozenset(),
            expected_hidden_names=frozenset(
                {
                    "root",
                    "child_a",
                    "child_b",
                    "leaf_aa",
                    "leaf_ab",
                    "leaf_ba",
                }
            ),
        ),
    )

    def test_no_filter_all_nodes_visible(
        self,
        tree: Tree,
        all_nodes: List[TreeNode],
    ) -> None:
        for node in all_nodes:
            assert tree.is_node_visible(node)

    def test_is_filtered_false_initially(self, tree: Tree) -> None:
        assert not tree.is_filtered()

    def test_is_filtered_true_after_apply(self, tree: Tree) -> None:
        tree.apply_filter("root", name_predicate)
        assert tree.is_filtered()

    def test_filter_empty_query_clears_filter(self, tree: Tree) -> None:
        tree.apply_filter("child_a", name_predicate)
        tree.apply_filter("", name_predicate)
        assert not tree.is_filtered()

    def test_clear_filter_makes_all_nodes_visible(
        self,
        tree: Tree,
        all_nodes: List[TreeNode],
    ) -> None:
        tree.apply_filter("leaf_ba", name_predicate)
        tree.clear_filter()
        for node in all_nodes:
            assert tree.is_node_visible(node)

    def test_filter_on_empty_tree_is_active(self) -> None:
        t = Tree()
        t.apply_filter("x", name_predicate)
        assert t.is_filtered()

    @pytest.mark.parametrize("case", test_cases, ids=lambda c: c.label)
    def test_filter_visibility(
        self,
        tree: Tree,
        all_nodes: List[TreeNode],
        case: TestCase,
    ) -> None:
        tree.apply_filter(case.query, name_predicate)
        for node in all_nodes:
            if node.name in case.expected_visible_names:
                assert tree.is_node_visible(node), f"{node.name!r} should be visible for query {case.query!r}"
            elif node.name in case.expected_hidden_names:
                assert not tree.is_node_visible(node), f"{node.name!r} should be hidden for query {case.query!r}"


class TestTreeCollectLeaves:
    def test_returns_empty_for_empty_tree(self) -> None:
        assert Tree().collect_leaves() == []

    def test_singleton_root_is_its_own_leaf(self) -> None:
        root = TreeNode("root", NodeType.ROOT)
        t = Tree(root=root)
        leaves = t.collect_leaves()
        assert len(leaves) == 1
        assert leaves[0] is root

    def test_returns_all_leaves_without_filter(self, tree: Tree) -> None:
        leaf_names = {leaf.name for leaf in tree.collect_leaves()}
        assert leaf_names == {"leaf_aa", "leaf_ab", "leaf_ba"}

    def test_filtered_leaves_exclude_hidden(self, tree: Tree) -> None:
        tree.apply_filter("leaf_ba", name_predicate)
        leaves = tree.collect_leaves()
        assert len(leaves) == 1
        assert leaves[0].name == "leaf_ba"


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
