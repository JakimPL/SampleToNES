from dataclasses import dataclass
from typing import Dict, List

import pytest

from sampletones_core.structures.tree.node import TreeNode
from sampletones_core.structures.tree.type import NodeType
from sampletones_core.structures.tree.visibility import TreeVisibility, resolve_visibility
from tests.suite.case import BaseTestCase


@pytest.fixture
def nodes() -> Dict[str, TreeNode]:
    root = TreeNode("root", NodeType.ROOT)
    child_a = TreeNode("child_a", NodeType.DIRECTORY, parent=root)
    child_b = TreeNode("child_b", NodeType.DIRECTORY, parent=root)
    leaf_aa = TreeNode("leaf_aa", NodeType.FILE, parent=child_a)
    leaf_ab = TreeNode("leaf_ab", NodeType.FILE, parent=child_a)
    leaf_ba = TreeNode("leaf_ba", NodeType.FILE, parent=child_b)
    return {
        node.name: node
        for node in (
            root,
            child_a,
            child_b,
            leaf_aa,
            leaf_ab,
            leaf_ba,
        )
    }


def visibility_of(
    nodes: Dict[str, TreeNode],
    matched_names: List[str],
) -> TreeVisibility:
    return resolve_visibility(nodes[name] for name in matched_names)


class TestVisibleRows:
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseTestCase):
        label: str
        matched_names: List[str]
        expected_visible_names: frozenset[str]

    test_cases = (
        TestCase(
            label="a_named_leaf_is_read_under_the_rows_holding_it",
            matched_names=["leaf_ba"],
            expected_visible_names=frozenset({"root", "child_b", "leaf_ba"}),
        ),
        TestCase(
            label="a_named_row_shows_what_it_gathers",
            matched_names=["child_a"],
            expected_visible_names=frozenset({"root", "child_a", "leaf_aa", "leaf_ab"}),
        ),
        TestCase(
            label="two_named_rows_each_keep_their_own_way_in",
            matched_names=["leaf_aa", "leaf_ba"],
            expected_visible_names=frozenset(
                {
                    "root",
                    "child_a",
                    "leaf_aa",
                    "child_b",
                    "leaf_ba",
                }
            ),
        ),
        TestCase(
            label="nothing_named_keeps_nothing",
            matched_names=[],
            expected_visible_names=frozenset(),
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_the_rows_a_match_keeps(
        self,
        nodes: Dict[str, TreeNode],
        case: TestCase,
    ) -> None:
        visibility = visibility_of(nodes, case.matched_names)
        visible_names = {name for name, node in nodes.items() if visibility.is_visible(node)}
        assert visible_names == case.expected_visible_names


class TestOpenRows:
    def test_every_row_above_a_match_stands_open(self, nodes: Dict[str, TreeNode]) -> None:
        visibility = visibility_of(nodes, ["leaf_ba"])
        open_names = {name for name, node in nodes.items() if visibility.should_expand(node)}
        assert open_names == {"root", "child_b", "leaf_ba"}

    def test_a_row_beside_the_way_in_stays_folded(self, nodes: Dict[str, TreeNode]) -> None:
        visibility = visibility_of(nodes, ["leaf_ba"])
        assert not visibility.should_expand(nodes["child_a"])

    def test_a_row_below_a_match_stays_folded(self, nodes: Dict[str, TreeNode]) -> None:
        """A match shows what it gathers as it stands, so its own rows keep the shape they had."""
        visibility = visibility_of(nodes, ["child_a"])
        assert visibility.is_visible(nodes["leaf_aa"])
        assert not visibility.should_expand(nodes["leaf_aa"])

    def test_nothing_named_leaves_every_row_folded(self, nodes: Dict[str, TreeNode]) -> None:
        visibility = visibility_of(nodes, [])
        assert not any(visibility.should_expand(node) for node in nodes.values())


class TestResolvedSets:
    def test_the_named_rows_are_held_as_they_were_given(self, nodes: Dict[str, TreeNode]) -> None:
        visibility = visibility_of(nodes, ["leaf_aa", "leaf_ab"])
        assert visibility.matches == frozenset({nodes["leaf_aa"], nodes["leaf_ab"]})

    def test_only_the_rows_above_a_match_are_held_beside_them(self, nodes: Dict[str, TreeNode]) -> None:
        """What a match holds is answered from a path, so the sets stay the size of what was found."""
        visibility = visibility_of(nodes, ["child_a"])
        assert visibility.ancestors == frozenset({nodes["root"]})

    def test_a_match_above_another_is_held_in_both_sets(self, nodes: Dict[str, TreeNode]) -> None:
        visibility = visibility_of(nodes, ["child_a", "leaf_aa"])
        assert nodes["child_a"] in visibility.matches
        assert nodes["child_a"] in visibility.ancestors
