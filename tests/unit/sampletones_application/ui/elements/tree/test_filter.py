from typing import Dict, List, Set, Type

from sampletones_application.ui.elements.tree.filter import NO_FILTER, TreeFilter
from sampletones_application.ui.panels.reconstruction.browser import GUIReconstructionsBrowserPanel
from sampletones_application.ui.panels.sequencer.browser import GUISequencerBrowserPanel
from sampletones_application.ui.panels.shared.browser import GUIReconstructionBrowserPanel
from sampletones_core.structures.tree import NodeType, Tree, TreeNode


class FakeTreeLogic:
    """Stands in for the logic a panel schedules the search on, recording what it was asked for."""

    def __init__(self) -> None:
        self.scheduled_queries: List[str] = []

    def schedule_search_update(self, query: str) -> None:
        self.scheduled_queries.append(query)


def browser_tree() -> Tree:
    """Builds the shape both browser views give one reconstructions directory, a row per label."""
    root = TreeNode("Root", node_type=NodeType.ROOT)
    configurations = TreeNode("By configuration", node_type=NodeType.GROUP, parent=root)
    TreeNode("song", node_type=NodeType.FILE, parent=configurations)
    TreeNode("other", node_type=NodeType.FILE, parent=configurations)
    samples = TreeNode("By sample", node_type=NodeType.GROUP, parent=root)
    sample = TreeNode("sample", node_type=NodeType.SAMPLE, parent=samples)
    TreeNode("variant", node_type=NodeType.FILE, parent=sample)
    return Tree(root=root)


def rows_of(tree: Tree) -> Dict[str, TreeNode]:
    """The rows a tree holds, read by the label each of them carries."""
    root = tree.get_root()
    assert root is not None
    return {node.name: node for node in (root, *root.descendants)}


def build_panel(
    tree: Tree,
    panel_class: Type[GUIReconstructionBrowserPanel] = GUISequencerBrowserPanel,
) -> GUIReconstructionBrowserPanel:
    """Builds a browser panel holding a filter, with the tree it reads and the logic it schedules on.

    Resolving a filter reads the model alone, so the panel needs neither widgets nor a search box.
    """
    panel = panel_class.__new__(panel_class)
    panel.tree = tree
    panel._logic = FakeTreeLogic()
    panel._search_input_tag = None
    panel._filter = NO_FILTER
    panel._search_visibility = None
    panel._favorites_visibility = None
    return panel


def visible_rows(panel: GUIReconstructionBrowserPanel, tree: Tree) -> Set[str]:
    return {name for name, node in rows_of(tree).items() if panel._is_node_visible(node)}


class TestFilterComposition:
    def test_a_filter_stating_nothing_narrows_nothing(self) -> None:
        assert not NO_FILTER.is_active

    def test_a_filter_carrying_a_query_narrows(self) -> None:
        assert NO_FILTER.with_query("song").is_active

    def test_dropping_the_query_leaves_the_filter_narrowing_nothing(self) -> None:
        assert not NO_FILTER.with_query("song").with_query("").is_active

    def test_a_filter_showing_the_favorites_alone_narrows(self) -> None:
        assert NO_FILTER.with_favorites_only(True).is_active

    def test_the_query_and_the_favorites_mode_are_stated_side_by_side(self) -> None:
        tree_filter = NO_FILTER.with_query("song").with_favorites_only(True)
        assert tree_filter.query == "song"
        assert tree_filter.favorites_only

    def test_the_filter_a_new_one_was_taken_from_reads_as_it_did(self) -> None:
        original = TreeFilter(query="song", favorites_only=False)
        original.with_query("other")
        original.with_favorites_only(True)
        assert original.query == "song"
        assert not original.favorites_only


class TestPanelOwnedFilter:
    def test_a_query_shows_the_rows_it_names_and_the_rows_above_them(self) -> None:
        tree = browser_tree()
        panel = build_panel(tree)

        panel._on_search_changed(None, "other")

        assert visible_rows(panel, tree) == {"Root", "By configuration", "other"}

    def test_a_query_naming_a_container_shows_what_it_gathers(self) -> None:
        tree = browser_tree()
        panel = build_panel(tree)

        panel._on_search_changed(None, "sample")

        assert visible_rows(panel, tree) == {"Root", "By sample", "sample", "variant"}

    def test_no_query_shows_every_row(self) -> None:
        tree = browser_tree()
        panel = build_panel(tree)

        assert visible_rows(panel, tree) == set(rows_of(tree))

    def test_clearing_the_search_shows_every_row_again(self) -> None:
        tree = browser_tree()
        panel = build_panel(tree)

        panel._on_search_changed(None, "other")
        panel._on_clear_search_clicked()

        assert visible_rows(panel, tree) == set(rows_of(tree))

    def test_the_search_is_scheduled_as_it_is_typed_and_as_it_is_cleared(self) -> None:
        tree = browser_tree()
        panel = build_panel(tree)
        logic = panel._logic

        panel._on_search_changed(None, "oth")
        panel._on_clear_search_clicked()

        assert logic.scheduled_queries == ["oth", ""]


class TestTwoPanelsOverOneTree:
    """Both reconstruction browsers render one tree, and each of them narrows to its own filter."""

    def test_a_query_in_one_panel_leaves_the_other_reading_as_it_was(self) -> None:
        tree = browser_tree()
        searching = build_panel(tree, GUISequencerBrowserPanel)
        untouched = build_panel(tree, GUIReconstructionsBrowserPanel)

        searching._on_search_changed(None, "other")

        assert visible_rows(untouched, tree) == set(rows_of(tree))
        assert not untouched._filter.is_active

    def test_each_panel_narrows_to_the_query_it_was_given(self) -> None:
        tree = browser_tree()
        first = build_panel(tree, GUISequencerBrowserPanel)
        second = build_panel(tree, GUIReconstructionsBrowserPanel)

        first._on_search_changed(None, "other")
        second._on_search_changed(None, "variant")

        assert visible_rows(first, tree) == {"Root", "By configuration", "other"}
        assert visible_rows(second, tree) == {"Root", "By sample", "sample", "variant"}


class TestFilterAcrossARebuild:
    def test_a_query_answers_for_the_rows_a_refresh_brings(self) -> None:
        tree = browser_tree()
        panel = build_panel(tree)
        panel._on_search_changed(None, "arrival")

        root = TreeNode("Root", node_type=NodeType.ROOT)
        group = TreeNode("By configuration", node_type=NodeType.GROUP, parent=root)
        arrival = TreeNode("arrival", node_type=NodeType.FILE, parent=group)
        tree.set_root(root)
        panel._resolve_filter()

        assert panel._is_node_visible(arrival)
        assert visible_rows(panel, tree) == {"Root", "By configuration", "arrival"}


class TestExpandedRows:
    def test_a_row_leading_to_a_result_is_emitted_open(self) -> None:
        tree = browser_tree()
        panel = build_panel(tree)

        panel._on_search_changed(None, "other")

        assert panel._should_expand_node(rows_of(tree)["By configuration"])

    def test_a_row_beside_the_way_in_is_emitted_folded(self) -> None:
        tree = browser_tree()
        panel = build_panel(tree)

        panel._on_search_changed(None, "other")

        assert not panel._should_expand_node(rows_of(tree)["By sample"])

    def test_no_query_leaves_every_row_as_it_stands(self) -> None:
        tree = browser_tree()
        panel = build_panel(tree)

        assert not any(panel._should_expand_node(node) for node in rows_of(tree).values())
