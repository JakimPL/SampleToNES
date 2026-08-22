from pathlib import Path
from typing import List, Set, Tuple

import pytest

from sampletones_application.ui.elements.tree import tree as tree_module
from sampletones_application.ui.elements.tree.expansion import RowExpansionMemory
from sampletones_application.ui.panels.main import explorer as explorer_module
from sampletones_application.ui.panels.main.explorer import GUIExplorerPanel
from sampletones_core.structures.tree import FileSystemNode, NodeType, Tree, TreeNode

PANEL_TAG = "main_explorer"
ROOT = Path("/")
MUSIC = ROOT / "music"


class FakeExplorerLogic:
    """Answers what the panel asks of its model, recording what it is told about each folder."""

    def __init__(self, tree: Tree) -> None:
        self.tree = tree
        self.cleared: List[Tuple[str, ...]] = []
        self.loaded: Set[Path] = set()
        self.read: List[Path] = []
        self.standing: List[Tuple[Path, bool]] = []

    def has_loaded_children(self, filepath: Path) -> bool:
        return filepath in self.loaded

    def expand_directory(self, node: FileSystemNode) -> None:
        self.read.append(node.filepath)
        self.loaded.add(node.filepath)

    def set_directory_open(self, filepath: Path, is_open: bool) -> None:
        self.standing.append((filepath, is_open))

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
    panel._expansion = RowExpansionMemory(set())
    panel._explorer_logic = FakeExplorerLogic(tree)  # type: ignore[assignment]
    return panel


@pytest.fixture
def toggled(monkeypatch: pytest.MonkeyPatch) -> List[Tuple[str, bool]]:
    """Records the rows the panel folds through the framework, in place of the widgets."""
    calls: List[Tuple[str, bool]] = []
    monkeypatch.setattr(explorer_module.dpg, "does_item_exist", lambda tag: True)
    monkeypatch.setattr(explorer_module.dpg, "get_value", lambda tag: False)
    monkeypatch.setattr(
        explorer_module.dpg,
        "set_value",
        lambda tag, value: calls.append((tag, value)),
    )
    return calls


class TestFollowingAFold:
    """A click on a folder is how it opens, and the explorer is told what it now stands as."""

    def test_opening_a_folder_reads_it_and_records_it_open(
        self,
        toggled: List[Tuple[str, bool]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        tree = explorer_tree()
        panel = build_panel(tree)
        music = tree.find_nodes(FileSystemNode, lambda node: node.filepath == MUSIC)[0]
        monkeypatch.setattr(panel, "_rebuild_node_subtree", lambda node, node_tag: None, raising=False)

        panel._toggle_directory_expansion(music, "row.music")

        assert panel._explorer_logic.read == [MUSIC]
        assert panel._explorer_logic.standing == [(MUSIC, True)]
        assert toggled == [("row.music", True)]

    def test_a_folder_read_already_is_not_read_again(
        self,
        toggled: List[Tuple[str, bool]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        tree = explorer_tree()
        panel = build_panel(tree)
        music = tree.find_nodes(FileSystemNode, lambda node: node.filepath == MUSIC)[0]
        panel._explorer_logic.loaded.add(MUSIC)
        monkeypatch.setattr(panel, "_rebuild_node_subtree", lambda node, node_tag: None, raising=False)

        panel._toggle_directory_expansion(music, "row.music")

        assert panel._explorer_logic.read == []
        assert panel._explorer_logic.standing == [(MUSIC, True)]

    def test_folding_a_folder_records_it_closed(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        tree = explorer_tree()
        panel = build_panel(tree)
        music = tree.find_nodes(FileSystemNode, lambda node: node.filepath == MUSIC)[0]
        panel._explorer_logic.loaded.add(MUSIC)
        monkeypatch.setattr(explorer_module.dpg, "does_item_exist", lambda tag: True)
        monkeypatch.setattr(explorer_module.dpg, "get_value", lambda tag: True)
        monkeypatch.setattr(explorer_module.dpg, "set_value", lambda tag, value: None)

        panel._toggle_directory_expansion(music, "row.music")

        assert panel._explorer_logic.standing == [(MUSIC, False)]

    def test_a_row_that_left_the_tree_is_left_alone(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        tree = explorer_tree()
        panel = build_panel(tree)
        music = tree.find_nodes(FileSystemNode, lambda node: node.filepath == MUSIC)[0]
        monkeypatch.setattr(explorer_module.dpg, "does_item_exist", lambda tag: False)

        panel._toggle_directory_expansion(music, "row.music")

        assert panel._explorer_logic.standing == []


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


class FakeAutoplayLogic:
    """Answers the panel's request to preview a recording, recording what it was handed."""

    def __init__(self) -> None:
        self.played: List[FileSystemNode] = []

    def request_autoplay(self, node: FileSystemNode) -> None:
        self.played.append(node)


class RecordingClick:
    """A panel wired to record where a click on a recording went."""

    def __init__(self, *, can_add_stems: bool) -> None:
        tree = explorer_tree()
        self.panel = build_panel(tree)
        self.node = tree.find_nodes(FileSystemNode, lambda node: node.filepath == MUSIC / "song.wav")[0]
        self.autoplay = FakeAutoplayLogic()
        self.gathered: List[Path] = []
        self.selected: List[Path] = []
        self.panel._logic = self.autoplay  # type: ignore[assignment]
        self.panel.can_add_stems = lambda: can_add_stems
        self.panel.on_file_add_requested = self.gathered.append
        self.panel.on_wave_file_clicked = self.selected.append

    def click(self, monkeypatch: pytest.MonkeyPatch, *, holding_ctrl: bool) -> None:
        held = {explorer_module.Modifier.CTRL} if holding_ctrl else set()
        monkeypatch.setattr(explorer_module, "capture_modifiers", lambda: frozenset(held))
        self.panel._audio_node_clicked(self.node)


class TestClickingARecording:
    """Ctrl gathers a recording as a stem; a plain click hands it to the converter and plays it."""

    def test_a_plain_click_selects_the_recording_and_plays_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        clicked = RecordingClick(can_add_stems=True)

        clicked.click(monkeypatch, holding_ctrl=False)

        assert clicked.selected == [MUSIC / "song.wav"]
        assert clicked.autoplay.played == [clicked.node]
        assert clicked.gathered == []

    def test_holding_ctrl_gathers_the_recording_as_a_stem(self, monkeypatch: pytest.MonkeyPatch) -> None:
        clicked = RecordingClick(can_add_stems=True)

        clicked.click(monkeypatch, holding_ctrl=True)

        assert clicked.gathered == [MUSIC / "song.wav"]
        assert clicked.selected == []
        assert clicked.autoplay.played == []

    def test_a_busy_converter_leaves_ctrl_the_plain_click(self, monkeypatch: pytest.MonkeyPatch) -> None:
        clicked = RecordingClick(can_add_stems=False)

        clicked.click(monkeypatch, holding_ctrl=True)

        assert clicked.selected == [MUSIC / "song.wav"]
        assert clicked.gathered == []
