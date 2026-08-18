from pathlib import Path
from typing import List, Tuple

import pytest

from sampletones_application.ui.elements.tree import tree as tree_module
from sampletones_application.ui.panels.main.explorer import GUIExplorerPanel
from sampletones_core.structures.tree import FileSystemNode, NodeType, Tree, TreeNode

PANEL_TAG = "main_explorer"
ROOT = Path("/")
MUSIC = ROOT / "music"


class FakeExplorerLogic:
    """Answers what the panel asks of its model, recording the folders it is told to drop."""

    def __init__(self, tree: Tree) -> None:
        self.tree = tree
        self.cleared: List[Tuple[str, ...]] = []

    def collapse_all(self) -> None:
        root = self.tree.get_root()
        assert root is not None
        self.cleared.append(tuple(str(node.name) for node in root.descendants))
        for filesystem_node in list(root.children):
            for child in list(filesystem_node.children):
                child.parent = None


def explorer_tree() -> Tree:
    """A filesystem root holding a folder that holds a file, as the explorer lists them."""
    root = TreeNode("Root", node_type=NodeType.ROOT)
    filesystem = FileSystemNode(
        str(ROOT),
        node_type=NodeType.DIRECTORY,
        filepath=ROOT,
        parent=root,
    )
    music = FileSystemNode(
        MUSIC.name,
        node_type=NodeType.DIRECTORY,
        filepath=MUSIC,
        parent=filesystem,
    )
    FileSystemNode(
        "song.wav",
        node_type=NodeType.FILE,
        filepath=MUSIC / "song.wav",
        parent=music,
    )
    return Tree(root=root)


@pytest.fixture
def folded(monkeypatch: pytest.MonkeyPatch) -> List[Tuple[str, bool]]:
    calls: List[Tuple[str, bool]] = []
    monkeypatch.setattr(
        tree_module,
        "dpg_set_value",
        lambda tag, value: calls.append((tag, value)),
    )
    return calls


def build_panel(tree: Tree) -> GUIExplorerPanel:
    """Builds an explorer panel holding a tree, which is all folding its rows away reads."""
    panel = GUIExplorerPanel.__new__(GUIExplorerPanel)
    panel.tag = PANEL_TAG
    panel.tree = tree
    panel._expanded_rows = set()
    panel._explorer_logic = FakeExplorerLogic(tree)  # type: ignore[assignment]
    return panel


class TestCollapseAll:
    def test_the_rows_fold_while_the_model_still_states_them(
        self,
        folded: List[Tuple[str, bool]],
    ) -> None:
        """A folder is reached through the model, so the fold runs before its children are dropped."""
        tree = explorer_tree()
        panel = build_panel(tree)
        music = tree.find_nodes(FileSystemNode, lambda node: node.filepath == MUSIC)[0]
        music_tag = panel._generate_node_tag(music)

        panel._on_collapse_all_clicked()

        assert music_tag in {tag for tag, _ in folded}
        assert all(not expanded for _, expanded in folded)

    def test_the_folders_the_model_held_are_dropped_afterwards(
        self,
        folded: List[Tuple[str, bool]],
    ) -> None:
        tree = explorer_tree()
        panel = build_panel(tree)

        panel._on_collapse_all_clicked()

        assert panel._explorer_logic.cleared == [(str(ROOT), MUSIC.name, "song.wav")]
        root = tree.get_root()
        assert root is not None
        assert [str(node.name) for node in root.descendants] == [str(ROOT)]
