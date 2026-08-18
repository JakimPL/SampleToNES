from typing import Final

from sampletones_application.ui.elements.tree.tag import compose_node_tag
from sampletones_core.structures.tree import NodeType, TreeNode

PANEL_TAG: Final[str] = "sequencer.browser.panel"
OTHER_PANEL_TAG: Final[str] = "reconstructions.browser.panel"


def root() -> TreeNode:
    return TreeNode("Root", node_type=NodeType.ROOT)


def group(name: str, parent: TreeNode) -> TreeNode:
    return TreeNode(name, node_type=NodeType.GROUP, parent=parent)


def tag_of(node: TreeNode) -> str:
    return compose_node_tag(node, panel_tag=PANEL_TAG)


class TestReadability:
    def test_tag_states_the_panel_and_the_names_above_the_row(self) -> None:
        node = group("cw_amen02_165", group("Amen Breaks", root()))

        assert tag_of(node).startswith(f"{PANEL_TAG}.")
        assert "node_root_amen_breaks_cw_amen02_165" in tag_of(node)

    def test_one_node_keeps_one_tag(self) -> None:
        node = group("song", root())

        assert tag_of(node) == tag_of(node)

    def test_each_panel_names_the_row_its_own_way(self) -> None:
        """Both browsers render one tree, so a row reaches each panel under a tag of that panel."""
        node = group("song", root())

        assert compose_node_tag(node, panel_tag=PANEL_TAG) != compose_node_tag(node, panel_tag=OTHER_PANEL_TAG)


class TestDistinctRows:
    def test_a_folder_and_the_audio_beside_it_keep_their_own_tags(self) -> None:
        container = root()
        folder = group("song", container)
        audio = TreeNode("song", node_type=NodeType.SAMPLE, parent=container)

        assert tag_of(folder) != tag_of(audio)

    def test_names_differing_in_spacing_keep_their_own_tags(self) -> None:
        """``drums/kick`` and ``drums kick`` read alike as a name path and stand as two rows."""
        container = root()
        nested = group("kick", group("drums", container))
        spaced = group("drums kick", container)

        assert tag_of(nested) != tag_of(spaced)

    def test_names_differing_in_case_keep_their_own_tags(self) -> None:
        container = root()
        lowercase = group("song", container)
        capitalized = group("Song", container)

        assert tag_of(lowercase) != tag_of(capitalized)
