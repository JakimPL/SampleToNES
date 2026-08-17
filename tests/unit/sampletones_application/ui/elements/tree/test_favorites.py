from pathlib import Path
from typing import Final, List, Set, Tuple

import pytest

from sampletones_application.tags.general import (
    TAG_GLOBAL_THEME_DEFAULT,
    TAG_GLOBAL_THEME_FAVORITE_CHILD,
)
from sampletones_application.ui.elements.tree.filter import NO_FILTER
from sampletones_application.ui.elements.tree.handler import NodeHandler
from sampletones_application.ui.elements.tree.spec import NodeSpec
from sampletones_application.ui.elements.tree.state import TreeNodeState
from sampletones_application.ui.panels.sequencer.browser import GUISequencerBrowserPanel
from sampletones_core.structures.tree import FileSystemNode, NodeType, Tree, TreeNode

CONFIG_DIRECTORY: Final[Path] = Path("/reconstructions/sr_44100_nf_30")
SONG_PATH: Final[Path] = CONFIG_DIRECTORY / "song.stn"
OTHER_PATH: Final[Path] = CONFIG_DIRECTORY / "other.stn"

Repaints = List[Tuple[TreeNode, bool]]


class FakeTreeLogic:
    def __init__(self, favorites: Set[Path]) -> None:
        self._favorites = favorites

    def is_node_favorite(self, node: TreeNode) -> bool:
        return isinstance(node, FileSystemNode) and node.filepath in self._favorites

    def has_favorite_ancestor(self, node: FileSystemNode) -> bool:
        return any(directory in self._favorites for directory in node.filepath.parents)


def browser_tree() -> Tree:
    """Builds the shape both browser views give one reconstructions directory.

    The same reconstruction is listed by its configuration and again by the sample it came from, so
    one path reaches the panel as two rows.
    """
    root = TreeNode("Root", node_type=NodeType.ROOT)
    configurations = TreeNode("By configuration", node_type=NodeType.GROUP, parent=root)
    directory = FileSystemNode(
        "PTN",
        node_type=NodeType.DIRECTORY,
        filepath=CONFIG_DIRECTORY,
        parent=configurations,
    )
    FileSystemNode("song", node_type=NodeType.FILE, filepath=SONG_PATH, parent=directory)
    FileSystemNode("other", node_type=NodeType.FILE, filepath=OTHER_PATH, parent=directory)

    samples = TreeNode("By sample", node_type=NodeType.GROUP, parent=root)
    sample = TreeNode("song", node_type=NodeType.SAMPLE, parent=samples)
    FileSystemNode(
        "44.1 kHz·30 Hz",
        node_type=NodeType.FILE,
        filepath=SONG_PATH,
        parent=sample,
    )
    return Tree(root=root)


@pytest.fixture
def repaints() -> Repaints:
    return []


def build_panel(
    tree: Tree,
    favorites: Set[Path],
    repaints: Repaints,
    monkeypatch: pytest.MonkeyPatch,
) -> GUISequencerBrowserPanel:
    """Builds a browser panel that records the rows it would repaint.

    Repainting binds themes to widgets, so the theme pass stands in as a recorder here and the
    panel keeps only the tree and the logic the favorite pass reads.
    """
    panel = GUISequencerBrowserPanel.__new__(GUISequencerBrowserPanel)
    panel.tree = tree
    panel._filter = NO_FILTER
    panel._search_visibility = None
    panel._favorites_visibility = None
    panel._favorites_anchors = None
    panel._expanded_rows = set()
    monkeypatch.setattr(panel, "_logic", FakeTreeLogic(favorites), raising=False)
    monkeypatch.setattr(
        panel,
        "_reapply_theme_recursively",
        lambda node, has_favorite_ancestor=False: repaints.append((node, has_favorite_ancestor)),
        raising=False,
    )
    return panel


def rows_at(tree: Tree, filepath: Path) -> Tuple[FileSystemNode, ...]:
    """Answers the rows the tree holds for a path, as the browser's owner hands them to the panel."""
    return tree.find_nodes(FileSystemNode, lambda node: node.filepath == filepath)


def build_specs(
    tree: Tree,
    favorites: Set[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> List[NodeSpec]:
    """Collects the rows a browser refresh would emit for a tree, with the themes it resolves.

    The collecting pass runs off the main thread and touches no widget, so it needs only the tree,
    the logic it asks about favorites, and a tag per row.
    """
    panel = build_panel(tree, favorites, [], monkeypatch)
    panel._pending_specs = []
    panel._node_handlers = {
        node_type: NodeHandler(tag=f"handler.{node_type.value}", node_type=node_type) for node_type in NodeType
    }
    monkeypatch.setattr(panel, "_generate_node_tag", lambda node: f"row.{node.name}", raising=False)

    panel._build_tree_node(tree.get_root(), TreeNodeState(parent="tree"))
    return panel._pending_specs


def theme_of(specs: List[NodeSpec], label: str) -> str:
    return next(spec.theme_tag for spec in specs if spec.label == label)


class TestRowRepaint:
    def test_every_row_standing_for_the_path_repaints(
        self,
        repaints: Repaints,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        tree = browser_tree()
        panel = build_panel(tree, {SONG_PATH}, repaints, monkeypatch)

        panel.update_favorite_indicators(rows_at(tree, SONG_PATH))

        assert [node.name for node, _ in repaints] == ["song", "44.1 kHz·30 Hz"]

    def test_a_path_listed_once_repaints_once(
        self,
        repaints: Repaints,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        tree = browser_tree()
        panel = build_panel(tree, {OTHER_PATH}, repaints, monkeypatch)

        panel.update_favorite_indicators(rows_at(tree, OTHER_PATH))

        assert [node.name for node, _ in repaints] == ["other"]

    def test_a_path_the_tree_states_nowhere_repaints_nothing(
        self,
        repaints: Repaints,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        tree = browser_tree()
        panel = build_panel(tree, set(), repaints, monkeypatch)

        panel.update_favorite_indicators(rows_at(tree, Path("/elsewhere/song.stn")))

        assert repaints == []

    def test_a_favorite_directory_repaints_where_each_view_holds_it(
        self,
        repaints: Repaints,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        tree = browser_tree()
        panel = build_panel(tree, {CONFIG_DIRECTORY}, repaints, monkeypatch)

        panel.update_favorite_indicators(rows_at(tree, CONFIG_DIRECTORY))

        assert [node.name for node, _ in repaints] == ["PTN"]


class TestFavoriteAncestry:
    def test_each_row_repaints_with_the_ancestry_of_its_path(
        self,
        repaints: Repaints,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A favorite configuration directory tints the reconstruction in both views."""
        tree = browser_tree()
        panel = build_panel(tree, {CONFIG_DIRECTORY}, repaints, monkeypatch)

        panel.update_favorite_indicators(rows_at(tree, SONG_PATH))

        assert [has_favorite_ancestor for _, has_favorite_ancestor in repaints] == [True, True]

    def test_a_row_no_favorite_holds_repaints_plainly(
        self,
        repaints: Repaints,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        tree = browser_tree()
        panel = build_panel(tree, {SONG_PATH}, repaints, monkeypatch)

        panel.update_favorite_indicators(rows_at(tree, SONG_PATH))

        assert [has_favorite_ancestor for _, has_favorite_ancestor in repaints] == [False, False]


class TestFavoriteAncestryWhileBuilding:
    def test_a_directory_below_a_favorite_the_view_omits_is_tinted(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The reconstructions directory holds the row without being a row itself, and still counts."""
        tree = browser_tree()
        specs = build_specs(tree, {CONFIG_DIRECTORY.parent}, monkeypatch)
        assert theme_of(specs, "PTN") == TAG_GLOBAL_THEME_FAVORITE_CHILD

    def test_a_directory_no_favorite_holds_reads_plainly(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        tree = browser_tree()
        specs = build_specs(tree, set(), monkeypatch)
        assert theme_of(specs, "PTN") == TAG_GLOBAL_THEME_DEFAULT
