from typing import Iterator

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.ui.panels.sequencer.browser import GUISequencerBrowserPanel
from sampletones_core.structures.tree import NodeType, TreeNode
from tests.suite.language import FakeLanguageManager
from tests.suite.status import RecordedStatusBar


@pytest.fixture
def context() -> Iterator[None]:
    dpg.create_context()
    try:
        yield
    finally:
        dpg.destroy_context()


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


@pytest.mark.usefixtures("context")
class TestAHoverReportedAfterTheRowWent:
    def test_a_row_a_rebuild_removed_leaves_the_status_bar_as_it_was(self) -> None:
        """The hover arrives a frame late, and a row the rebuilt tree no longer holds says nothing."""
        status_bar = RecordedStatusBar()
        panel = _panel()
        panel._status_bar = status_bar
        hovered = panel._create_hover_callback(lambda *_args, **_kwargs: "row")
        with dpg.window():
            row = dpg.add_text("row")
        dpg.delete_item(row)

        hovered(0, row)

        assert status_bar.messages == []
