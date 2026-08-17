from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, FrozenSet, List, Set

import pytest

from sampletones_application.ui.elements.tree.filter import TreeFilter
from sampletones_application.ui.elements.tree.handler import NodeHandler
from sampletones_application.ui.elements.tree.spec import NodeSpec
from sampletones_application.ui.elements.tree.state import TreeNodeState
from sampletones_application.ui.panels.sequencer.browser import GUISequencerBrowserPanel
from sampletones_core.structures.tree import FileSystemNode, NodeType, Tree, TreeNode
from tests.suite.language import FakeLanguageManager

PANEL_TAG: Final[str] = "sequencer.browser"

CONFIG_DIRECTORY: Final[Path] = Path("/reconstructions/sr_44100_nf_30")
STARRED_PATH: Final[Path] = CONFIG_DIRECTORY / "starred.stn"
PLAIN_PATH: Final[Path] = CONFIG_DIRECTORY / "plain.stn"
VARIANT_LABEL: Final[str] = "44.1 kHz·30 Hz"

STARRED_ROWS: Final[FrozenSet[str]] = frozenset(
    {
        "configurations",
        "directory",
        "starred",
        "samples",
        "starred_sample",
        "starred_variant",
    }
)
SAMPLE_VIEW_ROWS: Final[FrozenSet[str]] = frozenset(
    {
        "samples",
        "starred_sample",
        "starred_variant",
        "plain_sample",
        "plain_variant",
    }
)


class FakeTreeLogic:
    """Answers the favorite questions a browser asks of its logic while it collects its rows."""

    def __init__(self, favorites: Set[Path]) -> None:
        self._favorites = favorites

    def is_node_favorite(self, node: TreeNode) -> bool:
        return isinstance(node, FileSystemNode) and node.filepath in self._favorites

    def has_favorite_ancestor(self, node: FileSystemNode) -> bool:
        return any(directory in self._favorites for directory in node.filepath.parents)


@dataclass(frozen=True)
class BrowserTree:
    """The shape both browser views give one configuration directory, with a handle on every row."""

    tree: Tree
    rows: Dict[str, TreeNode]


@pytest.fixture
def browser() -> BrowserTree:
    """Two reconstructions of one configuration, listed by that configuration and by their samples.

    A sample row carries the name of the reconstruction it gathers, the way the builder names it, so
    each row is held by a key of its own rather than by the label it reads under.
    """
    root = TreeNode("Root", node_type=NodeType.ROOT)
    configurations = TreeNode("By configuration", node_type=NodeType.GROUP, parent=root)
    directory = FileSystemNode(
        "PTN",
        node_type=NodeType.DIRECTORY,
        filepath=CONFIG_DIRECTORY,
        parent=configurations,
    )
    starred = FileSystemNode("starred", node_type=NodeType.FILE, filepath=STARRED_PATH, parent=directory)
    plain = FileSystemNode("plain", node_type=NodeType.FILE, filepath=PLAIN_PATH, parent=directory)

    samples = TreeNode("By sample", node_type=NodeType.GROUP, parent=root)
    starred_sample = TreeNode("starred", node_type=NodeType.SAMPLE, parent=samples)
    starred_variant = FileSystemNode(
        VARIANT_LABEL,
        node_type=NodeType.FILE,
        filepath=STARRED_PATH,
        parent=starred_sample,
    )
    plain_sample = TreeNode("plain", node_type=NodeType.SAMPLE, parent=samples)
    plain_variant = FileSystemNode(
        VARIANT_LABEL,
        node_type=NodeType.FILE,
        filepath=PLAIN_PATH,
        parent=plain_sample,
    )

    return BrowserTree(
        tree=Tree(root=root),
        rows={
            "configurations": configurations,
            "directory": directory,
            "starred": starred,
            "plain": plain,
            "samples": samples,
            "starred_sample": starred_sample,
            "starred_variant": starred_variant,
            "plain_sample": plain_sample,
            "plain_variant": plain_variant,
        },
    )


def build_panel(
    browser: BrowserTree,
    favorites: Set[Path],
    *,
    favorites_only: bool,
    query: str = "",
) -> GUISequencerBrowserPanel:
    """Builds a browser panel showing the tree under a filter, with the favorites its logic answers.

    Resolving the filter reads the model alone, so the panel needs neither widgets nor a search box.
    """
    panel = GUISequencerBrowserPanel.__new__(GUISequencerBrowserPanel)
    panel.tag = PANEL_TAG
    panel.tree = browser.tree
    panel._logic = FakeTreeLogic(favorites)
    panel._language_manager = FakeLanguageManager()
    panel._filter = TreeFilter(query=query, favorites_only=favorites_only)
    panel._resolve_filter()
    return panel


def collect_specs(panel: GUISequencerBrowserPanel) -> List[NodeSpec]:
    """Collects the rows a rebuild would emit, which is the pass running off the main thread."""
    panel._pending_specs = []
    panel._node_handlers = {
        node_type: NodeHandler(tag=f"handler.{node_type.value}", node_type=node_type) for node_type in NodeType
    }

    root = panel.tree.get_root()
    assert root is not None
    panel._build_tree_node(root, TreeNodeState(parent="tree"))
    return panel._pending_specs


def drawn_keys(
    browser: BrowserTree,
    specs: List[NodeSpec],
) -> Set[str]:
    drawn = {spec.node for spec in specs}
    return {key for key, node in browser.rows.items() if node in drawn}


def open_keys(
    browser: BrowserTree,
    specs: List[NodeSpec],
) -> Set[str]:
    standing_open = {spec.node for spec in specs if spec.should_expand}
    return {key for key, node in browser.rows.items() if node in standing_open}


class TestDrawnRows:
    def test_a_starred_reconstruction_is_drawn_under_the_rows_holding_it_in_both_views(
        self,
        browser: BrowserTree,
    ) -> None:
        panel = build_panel(browser, {STARRED_PATH}, favorites_only=True)
        assert drawn_keys(browser, collect_specs(panel)) == STARRED_ROWS

    def test_a_starred_directory_brings_the_reconstructions_it_holds(
        self,
        browser: BrowserTree,
    ) -> None:
        panel = build_panel(browser, {CONFIG_DIRECTORY}, favorites_only=True)
        assert {"directory", "starred", "plain"} <= drawn_keys(browser, collect_specs(panel))

    def test_a_starred_directory_reaches_the_view_holding_no_row_for_it(
        self,
        browser: BrowserTree,
    ) -> None:
        """The sample view lists reconstructions under their samples, and no row stands for a folder.

        Being held by a starred folder is read from the path, so each variant answers for itself and
        the sample gathering it comes along.
        """
        panel = build_panel(browser, {CONFIG_DIRECTORY}, favorites_only=True)
        assert SAMPLE_VIEW_ROWS <= drawn_keys(browser, collect_specs(panel))

    def test_nothing_starred_draws_no_row(self, browser: BrowserTree) -> None:
        panel = build_panel(browser, set(), favorites_only=True)
        assert collect_specs(panel) == []

    def test_the_mode_off_draws_every_row(self, browser: BrowserTree) -> None:
        panel = build_panel(browser, {STARRED_PATH}, favorites_only=False)
        assert drawn_keys(browser, collect_specs(panel)) == set(browser.rows)


class TestOpenRows:
    def test_the_rows_leading_to_a_favorite_stand_open(self, browser: BrowserTree) -> None:
        panel = build_panel(browser, {STARRED_PATH}, favorites_only=True)
        assert open_keys(browser, collect_specs(panel)) == {
            "configurations",
            "directory",
            "samples",
            "starred_sample",
        }

    def test_the_mode_off_leaves_every_row_as_it_stands(self, browser: BrowserTree) -> None:
        panel = build_panel(browser, {STARRED_PATH}, favorites_only=False)
        assert open_keys(browser, collect_specs(panel)) == set()


class TestSearchInsideTheMode:
    def test_the_mode_states_the_drawn_rows_while_the_query_states_the_shown_ones(
        self,
        browser: BrowserTree,
    ) -> None:
        panel = build_panel(browser, {STARRED_PATH}, favorites_only=True, query="starred")
        specs = collect_specs(panel)

        assert drawn_keys(browser, specs) == STARRED_ROWS
        assert panel._is_node_visible(browser.rows["starred"])
        assert not panel._is_node_visible(browser.rows["plain"])

    def test_a_query_naming_a_row_the_mode_leaves_out_shows_nothing_of_it(
        self,
        browser: BrowserTree,
    ) -> None:
        panel = build_panel(browser, {STARRED_PATH}, favorites_only=True, query="plain")
        assert "plain" not in drawn_keys(browser, collect_specs(panel))


class TestEmptyAnswer:
    """A rebuild drawing no row names the filter that answered so, where the rows would be."""

    def test_the_mode_finding_no_favorite_names_the_favorites(self, browser: BrowserTree) -> None:
        panel = build_panel(browser, set(), favorites_only=True)
        assert panel._empty_filter_message() == "global.dialog.message.tree_no_favorites"

    def test_a_query_finding_nothing_names_the_results(self, browser: BrowserTree) -> None:
        panel = build_panel(browser, set(), favorites_only=False, query="nothing")
        assert panel._empty_filter_message() == "global.dialog.message.tree_no_results"


class TestFavoriteChange:
    def test_a_change_draws_the_tree_again_while_the_mode_is_on(
        self,
        browser: BrowserTree,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = build_panel(browser, {STARRED_PATH}, favorites_only=True)
        redraws: List[bool] = []
        repaints: List[TreeNode] = []
        monkeypatch.setattr(panel, "redraw_tree", lambda: redraws.append(True), raising=False)
        monkeypatch.setattr(
            panel,
            "_reapply_theme_recursively",
            lambda node, has_favorite_ancestor=False: repaints.append(node),
            raising=False,
        )

        panel.update_favorite_indicators([browser.rows["starred"]])

        assert redraws == [True]
        assert repaints == []

    def test_a_change_repaints_the_rows_while_the_mode_is_off(
        self,
        browser: BrowserTree,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = build_panel(browser, {STARRED_PATH}, favorites_only=False)
        redraws: List[bool] = []
        repaints: List[TreeNode] = []
        monkeypatch.setattr(panel, "redraw_tree", lambda: redraws.append(True), raising=False)
        monkeypatch.setattr(
            panel,
            "_reapply_theme_recursively",
            lambda node, has_favorite_ancestor=False: repaints.append(node),
            raising=False,
        )

        panel.update_favorite_indicators([browser.rows["starred"], browser.rows["starred_variant"]])

        assert redraws == []
        assert repaints == [browser.rows["starred"], browser.rows["starred_variant"]]
