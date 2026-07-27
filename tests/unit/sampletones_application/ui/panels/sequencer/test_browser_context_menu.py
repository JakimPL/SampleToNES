import contextlib
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import pytest

from sampletones_application.ui.elements.tree import tree as tree_module
from sampletones_application.ui.panels.sequencer import browser as browser_module
from sampletones_application.ui.panels.sequencer.browser import GUISequencerBrowserPanel
from sampletones_core.structures.tree.node import FileSystemNode, NodeType

RECONSTRUCTION_PATH = Path("/reconstructions/kick_02.rec")

ADD_LABEL = "Add to Sequencer"
REPLACE_TEMPLATE = "Replace {sample}"


def _panel(replace_target: Optional[str]) -> GUISequencerBrowserPanel:
    """Builds a panel without its DearPyGui-dependent constructor.

    The sequencer context-menu builders touch only their hook attributes, the cached label
    strings, and ``CallbackMixin.call``, so a running GUI context is unnecessary. ``replace_target``
    stands in for whatever the samples panel currently has selected.
    """
    panel = GUISequencerBrowserPanel.__new__(GUISequencerBrowserPanel)
    panel._lbl_ctx_add_to_sequencer = ADD_LABEL
    panel._tpl_ctx_replace_sample = REPLACE_TEMPLATE
    panel.on_add_to_sequencer = None
    panel.can_add_to_sequencer = lambda: True
    panel.on_replace_in_sequencer = None
    panel.replace_in_sequencer_label = None if replace_target is None else lambda: replace_target
    return panel


def _node(node_type: NodeType = NodeType.FILE) -> FileSystemNode:
    return FileSystemNode(
        RECONSTRUCTION_PATH.name,
        node_type=node_type,
        filepath=RECONSTRUCTION_PATH,
    )


class _MenuItemRecorder:
    """Captures the keyword arguments of every menu item the builders register."""

    def __init__(self) -> None:
        self.items: List[Dict[str, Any]] = []
        self.separators = 0

    def add_menu_item(self, **kwargs: Any) -> int:
        self.items.append(kwargs)
        return 0

    def add_separator(self, **kwargs: Any) -> int:
        self.separators += 1
        return 0

    @property
    def labels(self) -> List[str]:
        return [item["label"] for item in self.items]

    def item(self, label: str) -> Dict[str, Any]:
        return next(item for item in self.items if item["label"] == label)


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _MenuItemRecorder:
    instance = _MenuItemRecorder()
    monkeypatch.setattr(tree_module.dpg, "add_menu_item", instance.add_menu_item)
    monkeypatch.setattr(tree_module.dpg, "add_separator", instance.add_separator)
    return instance


class TestReplaceItemVisibility:
    def test_absent_selection_offers_no_replacement(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel(replace_target=None)
        panel.replace_in_sequencer_label = lambda: None

        panel._add_context_menu_replace_item(_node())

        assert recorder.labels == []

    def test_unwired_provider_offers_no_replacement(self, recorder: _MenuItemRecorder) -> None:
        """A panel tolerates its hooks being unset until the coordinator wires them."""
        panel = _panel(replace_target=None)

        panel._add_context_menu_replace_item(_node())

        assert recorder.labels == []

    def test_selected_sample_is_named_in_the_label(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel(replace_target="1A: Bass")

        panel._add_context_menu_replace_item(_node())

        assert recorder.labels == ["Replace 1A: Bass"]

    def test_label_follows_the_selection_between_popups(self, recorder: _MenuItemRecorder) -> None:
        targets = iter(["00: Kick", "01: Snare"])
        panel = _panel(replace_target=None)
        panel.replace_in_sequencer_label = lambda: next(targets)

        panel._add_context_menu_replace_item(_node())
        panel._add_context_menu_replace_item(_node())

        assert recorder.labels == ["Replace 00: Kick", "Replace 01: Snare"]

    def test_replace_item_joins_the_add_items_separator_group(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel(replace_target="1A: Bass")

        panel._add_context_menu_sequencer_items(_node())
        panel._add_context_menu_replace_item(_node())

        assert recorder.labels == [ADD_LABEL, "Replace 1A: Bass"]
        assert recorder.separators == 1

    def test_shared_sequencer_items_carry_no_replacement(self, recorder: _MenuItemRecorder) -> None:
        """The shared builder offers only the add item, so a panel opts into replacement by call site."""
        panel = _panel(replace_target="1A: Bass")

        panel._add_context_menu_sequencer_items(_node())

        assert recorder.labels == [ADD_LABEL]


class TestAddItemEnablement:
    def test_predicate_decides_whether_the_add_item_is_live(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel(replace_target=None)
        panel.can_add_to_sequencer = lambda: False

        panel._add_context_menu_sequencer_items(_node())

        assert recorder.item(ADD_LABEL)["enabled"] is False

    def test_unwired_predicate_leaves_the_add_item_inert(self, recorder: _MenuItemRecorder) -> None:
        """An unanswered applicability question reaches the widget as a plain ``False``."""
        panel = _panel(replace_target=None)
        panel.can_add_to_sequencer = None

        panel._add_context_menu_sequencer_items(_node())

        assert recorder.item(ADD_LABEL)["enabled"] is False


class TestReconstructionMenuComposition:
    def test_replace_follows_the_add_item(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Pins the item order of the reconstruction menu, so replacement sits with the add item."""
        panel = _panel(replace_target="1A: Bass")
        built: List[str] = []
        for builder in (
            "_add_context_menu_text",
            "_add_context_menu_play_item",
            "_add_context_menu_sequencer_items",
            "_add_context_menu_replace_item",
            "_add_context_menu_path_items",
            "_add_context_menu_locate_audio_item",
            "_add_context_menu_favorite_item",
        ):
            monkeypatch.setattr(panel, builder, lambda _argument, name=builder: built.append(name))

        @contextlib.contextmanager
        def _menu() -> Iterator[None]:
            yield

        monkeypatch.setattr(browser_module, "context_menu", _menu)

        panel._show_reconstruction_context_menu(_node(), "node-tag")

        assert built == [
            "_add_context_menu_text",
            "_add_context_menu_play_item",
            "_add_context_menu_sequencer_items",
            "_add_context_menu_replace_item",
            "_add_context_menu_path_items",
            "_add_context_menu_locate_audio_item",
            "_add_context_menu_favorite_item",
        ]

    def test_directory_menu_offers_no_replacement(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel(replace_target="1A: Bass")
        built: List[str] = []
        for builder in (
            "_add_context_menu_text",
            "_add_context_menu_details",
            "_add_context_menu_path_items",
            "_add_context_menu_favorite_item",
        ):
            monkeypatch.setattr(panel, builder, lambda _argument, name=builder: built.append(name))

        @contextlib.contextmanager
        def _menu() -> Iterator[None]:
            yield

        monkeypatch.setattr(browser_module, "context_menu", _menu)

        panel._show_directory_context_menu(_node(NodeType.DIRECTORY))

        assert "_add_context_menu_replace_item" not in built


class TestReplaceItemDispatch:
    def test_clicking_reports_the_reconstruction_path(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel(replace_target="1A: Bass")
        requested: List[Path] = []
        panel.on_replace_in_sequencer = requested.append

        panel._add_context_menu_replace_item(_node())
        item = recorder.item("Replace 1A: Bass")
        item["callback"](0, None, item["user_data"])

        assert requested == [RECONSTRUCTION_PATH]

    def test_directory_node_requests_no_replacement(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel(replace_target="1A: Bass")
        requested: List[Path] = []
        panel.on_replace_in_sequencer = requested.append

        panel._on_replace_in_sequencer(0, None, _node(NodeType.DIRECTORY))

        assert requested == []
