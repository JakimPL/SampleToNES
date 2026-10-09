from typing import Final, List, Optional, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.tags.instructions import (
    TAG_INSTRUCTIONS_LIBRARY_THEME,
    TAG_INSTRUCTIONS_LIBRARY_THEME_OUTDATED,
)
from sampletones_application.ui.elements.tree.expansion import RowExpansionMemory
from sampletones_application.ui.elements.tree.handler import NodeHandler
from sampletones_application.ui.elements.tree.spec import NodeSpec
from sampletones_application.ui.elements.tree.state import TreeNodeState
from sampletones_application.ui.panels.instruction.library import GUIInstructionsLibraryPanel
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.library import InstructionLibraryKey
from sampletones_core.structures.tree import GeneratorNode, LibraryNode, NodeType, TreeNode
from tests.suite.language import FakeLanguageManager

STATUS_KEY: Final[str] = "instructions.library.message.status_node_generator"
STATUS_TEXT: Final[str] = "{generator} of {library_key}"
OUTDATED_KEY: Final[str] = "instructions.library.template.library_node_outdated_template"
OUTDATED_TEXT: Final[str] = "[!] {}"
LIBRARY_FILENAME: Final[str] = "library_abc123"


def _library_key() -> InstructionLibraryKey:
    return InstructionLibraryKey(
        sample_rate=44100,
        frame_length=1470,
        window_size=2940,
        transformation_gamma=100,
        config_hash="abc123",
        filename=LIBRARY_FILENAME,
    )


def _generator_node() -> GeneratorNode:
    library = LibraryNode("Library", library_key=_library_key(), outdated=False)
    return GeneratorNode("Pulse", generator_name=GeneratorName.PULSE, parent=library)


def _panel() -> GUIInstructionsLibraryPanel:
    panel = GUIInstructionsLibraryPanel.__new__(GUIInstructionsLibraryPanel)
    panel._language_manager = FakeLanguageManager(texts={STATUS_KEY: STATUS_TEXT, OUTDATED_KEY: OUTDATED_TEXT})
    return panel


class FakeLibraryLogic:
    current_library_key: Optional[InstructionLibraryKey] = None


def _build_specs(root: TreeNode, monkeypatch: pytest.MonkeyPatch) -> List[NodeSpec]:
    """Collects the rows a tree refresh would emit, which the traversal resolves off the main thread."""
    panel = _panel()
    panel._search_visibility = None
    panel._favorites_visibility = None
    panel._expansion = RowExpansionMemory(set())
    panel._pending_specs = []
    panel._node_handlers = {
        node_type: NodeHandler(tag=f"handler.{node_type.value}", node_type=node_type) for node_type in NodeType
    }
    monkeypatch.setattr(panel, "_library_logic", FakeLibraryLogic(), raising=False)
    monkeypatch.setattr(panel, "_generate_node_tag", lambda node: f"row.{node.name}", raising=False)

    panel._build_tree_node(root, TreeNodeState(parent="tree"))
    return panel._pending_specs


class TestGeneratorNodeMessage:
    def test_the_message_names_the_generator_and_its_library(self) -> None:
        """Hovering a generator row says which generator of which library it stands for."""
        panel = _panel()
        message_function = panel._create_status_bar_message_function_for_instructions_node()

        message = message_function(user_data=(_generator_node(), "row_tag"))

        assert message == f"{GeneratorName.PULSE} of {LIBRARY_FILENAME}"


class TestGeneratorNodeSelection:
    def test_a_click_names_the_library_and_the_generator(self) -> None:
        """Clicking a generator row hands on the library it belongs to and the generator it is."""
        panel = _panel()
        selected: List[Tuple[InstructionLibraryKey, GeneratorName]] = []
        panel.on_generator_selected = lambda library_key, generator_name: selected.append(
            (library_key, generator_name),
        )

        panel._on_generator_node_clicked(
            None,
            (dpg.mvMouseButton_Left, 0),
            (_generator_node(), "row_tag"),
        )

        assert selected == [(_library_key(), GeneratorName.PULSE)]

    def test_loading_from_the_row_menu_names_the_same_pair(self) -> None:
        """The row menu's load item reaches the generator the row holds, as a click does."""
        panel = _panel()
        selected: List[Tuple[InstructionLibraryKey, GeneratorName]] = []
        panel.on_generator_selected = lambda library_key, generator_name: selected.append(
            (library_key, generator_name),
        )

        panel._on_load_generator(None, True, _generator_node())

        assert selected == [(_library_key(), GeneratorName.PULSE)]


class TestTheRowOfALibrary:
    """A library another version built reads as out of date, while its name, which the row's
    tag and remembered expansion are built from, stays as it is."""

    def test_a_library_another_version_built_reads_as_out_of_date(self) -> None:
        node = LibraryNode("Library", library_key=_library_key(), outdated=True)

        assert (_panel()._node_label(node), node.name) == ("[!] Library", "Library")

    def test_a_library_this_build_reads_reads_as_its_name(self) -> None:
        node = LibraryNode("Library", library_key=_library_key(), outdated=False)

        assert _panel()._node_label(node) == "Library"

    @pytest.mark.parametrize(
        ("outdated", "theme"),
        [(True, TAG_INSTRUCTIONS_LIBRARY_THEME_OUTDATED), (False, TAG_INSTRUCTIONS_LIBRARY_THEME)],
        ids=["built by another version", "read by this build"],
    )
    def test_a_library_row_takes_the_theme_of_its_standing(self, outdated: bool, theme: str) -> None:
        node = LibraryNode("Library", library_key=_library_key(), outdated=outdated)

        assert _panel()._resolve_node_theme_tag(node) == theme


class TestTheRowsTheTreeDraws:
    def test_a_row_holding_nothing_is_drawn_as_a_leaf(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A library another version built lists no generators, so its row stands as a leaf."""
        root = TreeNode("Libraries", node_type=NodeType.ROOT)
        LibraryNode("Outdated", library_key=_library_key(), outdated=True, parent=root)
        current = LibraryNode("Current", library_key=_library_key(), outdated=False, parent=root)
        GeneratorNode("Pulse", generator_name=GeneratorName.PULSE, parent=current)

        specs = _build_specs(root, monkeypatch)

        assert {spec.node.name: spec.leaf for spec in specs} == {"Outdated": True, "Current": False, "Pulse": True}
