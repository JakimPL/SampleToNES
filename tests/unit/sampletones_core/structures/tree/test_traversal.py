from dataclasses import dataclass
from typing import Any, List, Optional

import pytest

from sampletones_core.structures.tree.node import TreeNode
from sampletones_core.structures.tree.traversal import TreeTraversal, traverse
from sampletones_core.structures.tree.type import NodeType
from tests.suite.case import BaseTestCase

DFS_ORDER = ["root", "child_a", "leaf_aa", "leaf_ab", "child_b", "leaf_ba"]
BFS_ORDER = ["root", "child_a", "child_b", "leaf_aa", "leaf_ab", "leaf_ba"]
ALL_NAMES = frozenset(DFS_ORDER)


@dataclass(frozen=True, kw_only=True)
class StrategyCase(BaseTestCase):
    label: str
    strategy: TreeTraversal


@dataclass(frozen=True, kw_only=True)
class OrderCase(StrategyCase):
    expected_order: List[str]


STRATEGY_CASES = [
    StrategyCase(label="dfs", strategy=TreeTraversal.DFS),
    StrategyCase(label="bfs", strategy=TreeTraversal.BFS),
]

ORDER_CASES = [
    OrderCase(label="dfs", strategy=TreeTraversal.DFS, expected_order=DFS_ORDER),
    OrderCase(label="bfs", strategy=TreeTraversal.BFS, expected_order=BFS_ORDER),
]


@pytest.fixture
def six_node_tree() -> TreeNode:
    root = TreeNode("root", NodeType.ROOT)
    child_a = TreeNode("child_a", NodeType.DIRECTORY, parent=root)
    child_b = TreeNode("child_b", NodeType.DIRECTORY, parent=root)
    TreeNode("leaf_aa", NodeType.FILE, parent=child_a)
    TreeNode("leaf_ab", NodeType.FILE, parent=child_a)
    TreeNode("leaf_ba", NodeType.FILE, parent=child_b)
    return root


class TestTraversalOrder:
    @pytest.mark.parametrize("case", ORDER_CASES, ids=lambda c: c.label)
    def test_traversal_visits_nodes_in_order(
        self,
        six_node_tree: TreeNode,
        case: OrderCase,
    ) -> None:
        visited: List[str] = []

        def collect(node: TreeNode) -> None:
            visited.append(node.name)

        traverse(case.strategy, method=False)(collect)(six_node_tree)
        assert visited == case.expected_order

    @pytest.mark.parametrize("case", STRATEGY_CASES, ids=lambda c: c.label)
    def test_traversal_visits_all_nodes(
        self,
        six_node_tree: TreeNode,
        case: StrategyCase,
    ) -> None:
        visited: List[str] = []

        def collect(node: TreeNode) -> None:
            visited.append(node.name)

        traverse(case.strategy, method=False)(collect)(six_node_tree)
        assert frozenset(visited) == ALL_NAMES

    @pytest.mark.parametrize("case", STRATEGY_CASES, ids=lambda c: c.label)
    def test_traversal_visits_root_first(
        self,
        six_node_tree: TreeNode,
        case: StrategyCase,
    ) -> None:
        visited: List[str] = []

        def collect(node: TreeNode) -> None:
            visited.append(node.name)

        traverse(case.strategy, method=False)(collect)(six_node_tree)
        assert visited[0] == "root"


class TestDFS:
    def test_kwargs_reach_callback(self, six_node_tree: TreeNode) -> None:
        received: List[Optional[str]] = []

        def collect(node: TreeNode, **kwargs: Any) -> None:
            received.append(kwargs.get("tag"))  # type: ignore[arg-type]

        traverse(TreeTraversal.DFS, method=False)(collect)(six_node_tree, tag="hello")
        assert received == ["hello"] * 6

    def test_function_callback_receives_node_as_first_arg(self, six_node_tree: TreeNode) -> None:
        first_arg: List[TreeNode] = []

        def collect(node: TreeNode) -> None:
            first_arg.append(node)

        traverse(TreeTraversal.DFS, method=False)(collect)(six_node_tree)
        assert first_arg[0] is six_node_tree


class TestTraverseInvalidStrategy:
    def test_unsupported_strategy_raises_on_call(self, six_node_tree: TreeNode) -> None:
        wrapped = traverse("unsupported_strategy", method=False)(lambda node: None)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="Unsupported traversal type"):
            wrapped(six_node_tree)


class TestSingleNode:
    @pytest.mark.parametrize("case", STRATEGY_CASES, ids=lambda c: c.label)
    def test_visits_exactly_once(self, case: StrategyCase) -> None:
        root = TreeNode("root", NodeType.ROOT)
        visited: List[str] = []

        def collect(node: TreeNode) -> None:
            visited.append(node.name)

        traverse(case.strategy, method=False)(collect)(root)
        assert visited == ["root"]
