import pytest

from sampletones_application.ui.panels.sequencer.browser import GUISequencerBrowserPanel
from sampletones_core.structures.tree import NodeType, TreeNode
from tests.suite.language import FakeLanguageManager


def _panel() -> GUISequencerBrowserPanel:
    panel = GUISequencerBrowserPanel.__new__(GUISequencerBrowserPanel)
    panel._language_manager = FakeLanguageManager()
    return panel


class TestExpandableNodeMessage:
    @pytest.mark.parametrize(
        ("node_type", "key"),
        [
            (NodeType.GROUP, "global.status.message.node_group"),
            (NodeType.SAMPLE, "global.status.message.node_sample"),
            (NodeType.DIRECTORY, "global.status.message.node_directory"),
        ],
    )
    def test_the_message_names_what_the_row_holds(
        self,
        node_type: NodeType,
        key: str,
    ) -> None:
        """Each row the reader opens holds something of its own, and its hover message says so."""
        panel = _panel()

        assert panel._expandable_node_message(TreeNode("row", node_type=node_type)) == key
