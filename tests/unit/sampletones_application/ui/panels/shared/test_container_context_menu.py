import contextlib
from pathlib import Path
from typing import Any, Dict, Final, Iterator, List, Optional, Sequence, Tuple

import pytest

from sampletones_application.ui.elements.tree import tree as tree_module
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.ui.elements.tree.tag import compose_node_tag
from sampletones_application.ui.panels.sequencer.browser import GUISequencerBrowserPanel
from sampletones_application.ui.panels.shared import browser as shared_browser_module
from sampletones_application.utils.palette.colors.literal import LiteralColor
from sampletones_core.structures.tree.node import FileSystemNode, NodeType, TreeNode
from tests.suite.language import FakeLanguageManager

PANEL_TAG = "sequencer_browser"

TEXT_COLOR = LiteralColor((128, 128, 128, 255))

EXPAND_LABEL = "Expand all"
COLLAPSE_LABEL = "Collapse all"
COPY_NAME_LABEL = "Copy name"
LOCATE_AUDIO_LABEL = "Locate original audio"
RECONSTRUCTIONS_LABEL = "Reconstructions"

TEXTS: Final[Dict[str, str]] = {
    "global.context.label.expand_all": EXPAND_LABEL,
    "global.context.label.collapse_all": COLLAPSE_LABEL,
    "global.context.label.copy_name": COPY_NAME_LABEL,
    "global.context.label.locate_original_audio": LOCATE_AUDIO_LABEL,
    "global.context.label.detail_reconstructions": RECONSTRUCTIONS_LABEL,
}

CONTAINER_BUILDERS: Final[Tuple[str, ...]] = (
    "_add_context_menu_text",
    "_add_context_menu_reconstruction_count",
    "_add_context_menu_expansion_items",
    "_add_context_menu_copy_name_item",
    "_add_context_menu_sample_audio_item",
)


def _panel() -> GUISequencerBrowserPanel:
    """Builds a panel without its DearPyGui-dependent constructor.

    The container menu reads the tree, the language manager and the panel tag its node tags are
    composed under, so a running GUI context is unnecessary.
    """
    panel = GUISequencerBrowserPanel.__new__(GUISequencerBrowserPanel)
    panel.tag = PANEL_TAG
    panel._language_manager = FakeLanguageManager(TEXTS)
    panel._colors = TreeColors(
        favorite=TEXT_COLOR,
        node=TEXT_COLOR,
        muted=TEXT_COLOR,
        accent=TEXT_COLOR,
    )
    panel.on_locate_original_audio = None
    return panel


def _sample_tree() -> Tuple[TreeNode, TreeNode, Sequence[FileSystemNode]]:
    """One sample gathering two configuration variants, under a frequency group."""
    root = TreeNode("root", node_type=NodeType.ROOT)
    group = TreeNode("44.1 kHz", node_type=NodeType.GROUP, parent=root)
    sample = TreeNode("kick.wav", node_type=NodeType.SAMPLE, parent=group)
    variants = [
        FileSystemNode(
            name,
            node_type=NodeType.FILE,
            filepath=Path("/reconstructions") / name,
            parent=sample,
        )
        for name in ("fft.stn", "cqt.stn")
    ]
    return group, sample, variants


class _MenuItemRecorder:
    """Captures the keyword arguments of every menu item the builders register."""

    def __init__(self) -> None:
        self.items: List[Dict[str, Any]] = []
        self.separators = 0
        self.clipboard: List[str] = []

    def add_menu_item(self, **kwargs: Any) -> int:
        self.items.append(kwargs)
        return 0

    def add_separator(self, **kwargs: Any) -> int:
        self.separators += 1
        return 0

    def set_clipboard_text(self, text: str) -> None:
        self.clipboard.append(text)

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
    monkeypatch.setattr(tree_module.dpg, "set_clipboard_text", instance.set_clipboard_text)
    return instance


@pytest.fixture
def expanded(monkeypatch: pytest.MonkeyPatch) -> List[Tuple[str, bool]]:
    """Records the tag and open state of every row the expansion items reach."""
    calls: List[Tuple[str, bool]] = []
    monkeypatch.setattr(
        shared_browser_module,
        "dpg_set_value",
        lambda tag, value: calls.append((tag, value)),
    )
    return calls


@pytest.fixture
def details(monkeypatch: pytest.MonkeyPatch) -> List[Sequence[Tuple[str, str]]]:
    """Records each block of read-only lines the menu states."""
    blocks: List[Sequence[Tuple[str, str]]] = []
    monkeypatch.setattr(
        shared_browser_module,
        "add_detail_items",
        lambda items, **_kwargs: blocks.append(items),
    )
    return blocks


@pytest.fixture
def built(monkeypatch: pytest.MonkeyPatch) -> List[str]:
    """Replaces every container-menu builder with a record of its name, in call order."""
    names: List[str] = []

    @contextlib.contextmanager
    def _menu() -> Iterator[None]:
        yield

    monkeypatch.setattr(shared_browser_module, "context_menu", _menu)
    return names


def _record_builders(
    panel: GUISequencerBrowserPanel,
    built: List[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for builder in CONTAINER_BUILDERS:
        monkeypatch.setattr(panel, builder, lambda _argument, name=builder: built.append(name))


class TestContainerMenuComposition:
    def test_group_row_states_what_it_holds_before_what_it_offers(
        self,
        built: List[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = _panel()
        group, _, _ = _sample_tree()
        _record_builders(panel, built, monkeypatch)

        panel._show_container_context_menu(group)

        assert built == list(CONTAINER_BUILDERS)

    def test_sample_row_offers_the_same_items(
        self,
        built: List[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = _panel()
        _, sample, _ = _sample_tree()
        _record_builders(panel, built, monkeypatch)

        panel._show_container_context_menu(sample)

        assert built == list(CONTAINER_BUILDERS)

    @pytest.mark.parametrize("node_type", [NodeType.FILE, NodeType.DIRECTORY, NodeType.ROOT])
    def test_row_standing_for_a_path_opens_no_container_menu(
        self,
        built: List[str],
        monkeypatch: pytest.MonkeyPatch,
        node_type: NodeType,
    ) -> None:
        """The rows with a path of their own have menus of their own, offering the path items."""
        panel = _panel()
        node = FileSystemNode("kick.stn", node_type=node_type, filepath=Path("/kick.stn"))
        _record_builders(panel, built, monkeypatch)

        panel._show_container_context_menu(node)

        assert built == []


class TestReconstructionCount:
    def test_sample_row_counts_the_variants_it_gathers(
        self,
        details: List[Sequence[Tuple[str, str]]],
    ) -> None:
        panel = _panel()
        _, sample, _ = _sample_tree()

        panel._add_context_menu_reconstruction_count(sample)

        assert details == [[(RECONSTRUCTIONS_LABEL, "2")]]

    def test_group_row_counts_every_reconstruction_below_it(
        self,
        details: List[Sequence[Tuple[str, str]]],
    ) -> None:
        """A group reports the whole subtree, so the containers between it and the files add nothing."""
        panel = _panel()
        group, sample, _ = _sample_tree()
        second_sample = TreeNode("snare.wav", node_type=NodeType.SAMPLE, parent=group)
        FileSystemNode(
            "fft.stn",
            node_type=NodeType.FILE,
            filepath=Path("/reconstructions/snare/fft.stn"),
            parent=second_sample,
        )

        panel._add_context_menu_reconstruction_count(group)

        assert details == [[(RECONSTRUCTIONS_LABEL, "3")]]

    def test_row_gathering_nothing_reports_no_reconstruction(
        self,
        details: List[Sequence[Tuple[str, str]]],
    ) -> None:
        panel = _panel()
        group = TreeNode("44.1 kHz", node_type=NodeType.GROUP)

        panel._add_context_menu_reconstruction_count(group)

        assert details == [[(RECONSTRUCTIONS_LABEL, "0")]]


class TestExpansionItems:
    def test_both_directions_are_offered(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel()
        group, _, _ = _sample_tree()

        panel._add_context_menu_expansion_items(group)

        assert recorder.labels == [EXPAND_LABEL, COLLAPSE_LABEL]

    def test_expanding_reaches_the_row_and_every_container_below_it(
        self,
        recorder: _MenuItemRecorder,
        expanded: List[Tuple[str, bool]],
    ) -> None:
        panel = _panel()
        group, sample, _ = _sample_tree()

        panel._add_context_menu_expansion_items(group)
        recorder.item(EXPAND_LABEL)["callback"]()

        assert expanded == [
            (compose_node_tag(group, panel_tag=PANEL_TAG), True),
            (compose_node_tag(sample, panel_tag=PANEL_TAG), True),
        ]

    def test_collapsing_closes_the_same_rows(
        self,
        recorder: _MenuItemRecorder,
        expanded: List[Tuple[str, bool]],
    ) -> None:
        panel = _panel()
        group, sample, _ = _sample_tree()

        panel._add_context_menu_expansion_items(group)
        recorder.item(COLLAPSE_LABEL)["callback"]()

        assert expanded == [
            (compose_node_tag(group, panel_tag=PANEL_TAG), False),
            (compose_node_tag(sample, panel_tag=PANEL_TAG), False),
        ]

    def test_leaf_rows_are_left_alone(
        self,
        recorder: _MenuItemRecorder,
        expanded: List[Tuple[str, bool]],
    ) -> None:
        """A reconstruction row holds nothing to fold, so no expansion state is stated for it."""
        panel = _panel()
        _, sample, variants = _sample_tree()

        panel._add_context_menu_expansion_items(sample)
        recorder.item(EXPAND_LABEL)["callback"]()

        variant_tags = [compose_node_tag(variant, panel_tag=PANEL_TAG) for variant in variants]
        assert [tag for tag, _ in expanded] == [compose_node_tag(sample, panel_tag=PANEL_TAG)]
        assert all(tag not in variant_tags for tag, _ in expanded)


class TestCopyNameItem:
    def test_clicking_copies_the_label_the_tree_reads(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel()
        group, _, _ = _sample_tree()

        panel._add_context_menu_copy_name_item(group)
        recorder.item(COPY_NAME_LABEL)["callback"]()

        assert recorder.clipboard == ["44.1 kHz"]

    def test_a_folded_chain_copies_every_level_of_its_label(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel()
        folded = TreeNode("44.1 kHz·30 Hz·FFT", node_type=NodeType.GROUP)

        panel._add_context_menu_copy_name_item(folded)
        recorder.item(COPY_NAME_LABEL)["callback"]()

        assert recorder.clipboard == ["44.1 kHz·30 Hz·FFT"]


class TestSampleAudioItem:
    def test_sample_row_delegates_to_a_reconstruction_below_it(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel()
        _, sample, variants = _sample_tree()

        panel._add_context_menu_sample_audio_item(sample)

        assert recorder.labels == [LOCATE_AUDIO_LABEL]
        assert recorder.item(LOCATE_AUDIO_LABEL)["user_data"] is variants[0]

    def test_clicking_reports_the_reconstruction_path(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel()
        _, sample, variants = _sample_tree()
        located: List[Path] = []
        panel.on_locate_original_audio = located.append

        panel._add_context_menu_sample_audio_item(sample)
        item = recorder.item(LOCATE_AUDIO_LABEL)
        item["callback"](0, None, item["user_data"])

        assert located == [variants[0].filepath]

    def test_group_row_offers_no_audio(self, recorder: _MenuItemRecorder) -> None:
        """A group gathers reconstructions of many samples, so no one audio stands behind it."""
        panel = _panel()
        group, _, _ = _sample_tree()

        panel._add_context_menu_sample_audio_item(group)

        assert recorder.labels == []

    def test_sample_row_holding_no_reconstruction_offers_no_audio(self, recorder: _MenuItemRecorder) -> None:
        panel = _panel()
        sample = TreeNode("kick.wav", node_type=NodeType.SAMPLE)

        panel._add_context_menu_sample_audio_item(sample)

        assert recorder.labels == []


class TestFirstReconstructionBelow:
    def test_the_nearest_reconstruction_answers_for_the_row(self) -> None:
        panel = _panel()
        _, sample, variants = _sample_tree()

        assert panel._first_reconstruction_below(sample) is variants[0]

    def test_a_row_gathering_none_names_nothing(self) -> None:
        panel = _panel()
        sample = TreeNode("kick.wav", node_type=NodeType.SAMPLE)

        assert panel._first_reconstruction_below(sample) is None

    def test_containers_below_the_row_are_passed_over(self) -> None:
        """A mirrored source folder under a group is not itself a reconstruction."""
        panel = _panel()
        group = TreeNode("44.1 kHz", node_type=NodeType.GROUP)
        directory = FileSystemNode(
            "drums",
            node_type=NodeType.DIRECTORY,
            filepath=Path("/reconstructions/drums"),
            parent=group,
        )
        reconstruction = FileSystemNode(
            "kick.stn",
            node_type=NodeType.FILE,
            filepath=Path("/reconstructions/drums/kick.stn"),
            parent=directory,
        )

        found: Optional[FileSystemNode] = panel._first_reconstruction_below(group)

        assert found is reconstruction
