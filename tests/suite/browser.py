from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Dict, Final, List, Mapping, Optional, Sequence, Set, Tuple

from sampletones_application.logic.reconstruction.browser.manager import BrowserManager
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.ui.elements.tree.filter import TreeFilter
from sampletones_application.ui.elements.tree.handler import NodeHandler
from sampletones_application.ui.elements.tree.spec import NodeSpec
from sampletones_application.ui.elements.tree.tree import GUITreePanel
from sampletones_application.ui.panels.sequencer.browser import GUISequencerBrowserPanel
from sampletones_application.utils.palette.colors.literal import LiteralColor
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.reconstructions.converter.paths import ConfigDirectoryFields
from sampletones_core.structures.tree import FileSystemNode, NodeType, Tree, TreeNode
from sampletones_shared.paths.extensions import EXT_FILE_RECONSTRUCTION
from tests.suite.language import FakeLanguageManager

PANEL_TAG: Final[str] = "sequencer.browser"
TREE_TAG: Final[str] = "sequencer.browser.tree"

HASH_A: Final[str] = "aaaaaaaa11111111aaaaaaaa11111111"
HASH_B: Final[str] = "bbbbbbbb22222222bbbbbbbb22222222"
HASH_C: Final[str] = "cccccccc33333333cccccccc33333333"
HASH_D: Final[str] = "dddddddd44444444dddddddd44444444"
HASH_E: Final[str] = "eeeeeeee55555555eeeeeeee55555555"
HASH_F: Final[str] = "ffffffff66666666ffffffff66666666"

ARCHIVE: Final[str] = "archive"
STRAY: Final[str] = "stray"

BROWSER_TEXTS: Final[Mapping[str, str]] = {
    "global.browser.label.root": "Root",
    "global.browser.label.by_configuration": "By configuration",
    "global.browser.label.by_sample": "By sample",
}

TREE_COLORS: Final[TreeColors] = TreeColors(
    favorite=LiteralColor((240, 200, 80, 255)),
    node=LiteralColor((200, 200, 200, 255)),
    muted=LiteralColor((120, 120, 120, 255)),
    accent=LiteralColor((80, 160, 240, 255)),
)

OPEN_MARKER: Final[str] = "v"
CLOSED_MARKER: Final[str] = ">"
LEAF_MARKER: Final[str] = "-"
HIDDEN_MARKER: Final[str] = "  [hidden]"
INDENT: Final[str] = "  "


def as_view(text: str) -> str:
    """Reads a view written as an indented block in a test, so the expected rows read as they draw."""
    return dedent(text).strip("\n")


WHOLE_TREE: Final[str] = as_view("""
    > By configuration
      > 8 kHz·60 Hz·CQT·γ2·P
        - sweep
      > 44.1 kHz·30 Hz
        > CQT·γ0·PTN
          - beat
          - solo
        > FFT·γ0
          > PT
            > takes
              - alt
            - beat
          > PTN·#aaaaaaa
            > drums
              - kick
              - snare
            - beat
            - melody
          > PTN·#bbbbbbb
            > drums
              - kick
            - beat
            - melody
      > archive
        > 48 kHz·50 Hz·LogFFT·γ1·TN
          - song
      - stray
    > By sample
      > beat
        - 44.1 kHz·30 Hz·CQT·γ0·PTN
        - 44.1 kHz·30 Hz·FFT·γ0·PT
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
      > drums
        > kick
          - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
          - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
        - snare·44.1 kHz·30 Hz·FFT·γ0·PTN
      > melody
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
      - solo·44.1 kHz·30 Hz·CQT·γ0·PTN
      - sweep·8 kHz·60 Hz·CQT·γ2·P
      - takes·alt·44.1 kHz·30 Hz·FFT·γ0·PT
    """)


def config_fields(
    *,
    sample_rate: int,
    nes_frequency: int,
    spectrum_method: SpectrumMethod,
    transformation_gamma: int,
    generators: str,
    config_hash: str,
) -> ConfigDirectoryFields:
    return ConfigDirectoryFields(
        sr=sample_rate,
        nf=nes_frequency,
        sm=spectrum_method,
        tg=transformation_gamma,
        gn=generators,
        ch=config_hash,
    )


CONFIG_A: Final[ConfigDirectoryFields] = config_fields(
    sample_rate=44100,
    nes_frequency=30,
    spectrum_method=SpectrumMethod.FFT,
    transformation_gamma=0,
    generators="PTN",
    config_hash=HASH_A,
)
CONFIG_B: Final[ConfigDirectoryFields] = config_fields(
    sample_rate=44100,
    nes_frequency=30,
    spectrum_method=SpectrumMethod.FFT,
    transformation_gamma=0,
    generators="PTN",
    config_hash=HASH_B,
)
CONFIG_C: Final[ConfigDirectoryFields] = config_fields(
    sample_rate=44100,
    nes_frequency=30,
    spectrum_method=SpectrumMethod.FFT,
    transformation_gamma=0,
    generators="PT",
    config_hash=HASH_C,
)
CONFIG_D: Final[ConfigDirectoryFields] = config_fields(
    sample_rate=44100,
    nes_frequency=30,
    spectrum_method=SpectrumMethod.CQT,
    transformation_gamma=0,
    generators="PTN",
    config_hash=HASH_D,
)
CONFIG_E: Final[ConfigDirectoryFields] = config_fields(
    sample_rate=8000,
    nes_frequency=60,
    spectrum_method=SpectrumMethod.CQT,
    transformation_gamma=2,
    generators="P",
    config_hash=HASH_E,
)
CONFIG_F: Final[ConfigDirectoryFields] = config_fields(
    sample_rate=48000,
    nes_frequency=50,
    spectrum_method=SpectrumMethod.LOG_SPACED_FFT,
    transformation_gamma=1,
    generators="TN",
    config_hash=HASH_F,
)

TOP_LEVEL_CONFIGURATIONS: Final[Mapping[str, ConfigDirectoryFields]] = {
    "A": CONFIG_A,
    "B": CONFIG_B,
    "C": CONFIG_C,
    "D": CONFIG_D,
    "E": CONFIG_E,
}
RECONSTRUCTIONS: Final[Mapping[str, Tuple[str, ...]]] = {
    "A": ("beat", "melody", "drums/kick", "drums/snare"),
    "B": ("beat", "melody", "drums/kick"),
    "C": ("beat", "takes/alt"),
    "D": ("beat", "solo"),
    "E": ("sweep",),
}


class FakeConfigManager:
    """Answers the one thing the browser manager asks of the configuration: where to read."""

    def __init__(self, reconstructions_directory: Path) -> None:
        self._reconstructions_directory = reconstructions_directory

    def get_reconstructions_directory(self) -> Path:
        return self._reconstructions_directory


class FakeTreeLogic:
    """Answers the favorite questions a browser asks of its logic while it collects its rows."""

    def __init__(
        self,
        favorites: Set[Path],
        *,
        auto_expand_reconstructions: bool,
        auto_expand_directories: bool,
    ) -> None:
        self._favorites = favorites
        self._auto_expand_reconstructions = auto_expand_reconstructions
        self._auto_expand_directories = auto_expand_directories

    def is_node_favorite(self, node: TreeNode) -> bool:
        return isinstance(node, FileSystemNode) and node.filepath in self._favorites

    def has_favorite_ancestor(self, node: FileSystemNode) -> bool:
        return any(directory in self._favorites for directory in node.filepath.parents)

    @property
    def auto_expand_favorite_reconstructions(self) -> bool:
        return self._auto_expand_reconstructions

    @property
    def auto_expand_favorite_directories(self) -> bool:
        return self._auto_expand_directories


@dataclass(frozen=True)
class BrowserCorpus:
    """A reconstructions directory read into the tree both browser views render.

    ``paths`` names every place a test can star: a configuration directory by its key, a
    reconstruction by ``"<key>/<relative name>"``, and the folders standing beside them.
    """

    tree: Tree
    paths: Mapping[str, Path]


def write_corpus(root: Path) -> Dict[str, Path]:
    """Writes the corpus the browser tests read, and answers where each part of it landed.

    The layout carries what the browser has to tell apart: two configurations differing by hash
    alone, a frequency holding several methods beside one holding a single chain, audio shared by
    every configuration and audio held by one, a configuration directory nested in a plain folder,
    and a reconstruction sitting outside every configuration directory.
    """
    paths: Dict[str, Path] = {}
    for key, fields in TOP_LEVEL_CONFIGURATIONS.items():
        directory = root / fields.directory_name
        paths[key] = directory
        for relative in RECONSTRUCTIONS[key]:
            paths[f"{key}/{relative}"] = _write_reconstruction(directory / relative)

    archive = root / ARCHIVE
    paths[ARCHIVE] = archive
    paths[f"{ARCHIVE}/F"] = archive / CONFIG_F.directory_name
    paths[f"{ARCHIVE}/F/song"] = _write_reconstruction(paths[f"{ARCHIVE}/F"] / "song")
    paths[STRAY] = _write_reconstruction(root / STRAY)
    return paths


def _write_reconstruction(path: Path) -> Path:
    reconstruction = path.with_suffix(EXT_FILE_RECONSTRUCTION)
    reconstruction.parent.mkdir(parents=True, exist_ok=True)
    reconstruction.touch()
    return reconstruction


def build_corpus(root: Path) -> BrowserCorpus:
    """Writes the corpus and reads it through the real pipeline, so the labels are the real ones."""
    paths = write_corpus(root)
    manager = BrowserManager(
        FakeConfigManager(root),  # type: ignore[arg-type]
        language_manager=FakeLanguageManager(texts=dict(BROWSER_TEXTS)),
    )
    manager.refresh_tree()
    return BrowserCorpus(
        tree=manager.tree,
        paths=paths,
    )


def build_browser_panel(
    corpus: BrowserCorpus,
    favorites: Set[Path],
    *,
    favorites_only: bool,
    query: str = "",
    panel_tag: str = PANEL_TAG,
    auto_expand_reconstructions: bool = False,
    auto_expand_directories: bool = False,
    expanded_rows: Optional[Set[str]] = None,
) -> GUISequencerBrowserPanel:
    """Builds a browser panel showing the corpus under a filter, with the favorites its logic answers.

    Resolving the filter reads the model alone, so the panel needs neither widgets nor a search box,
    and the control stands where a browser that has yet to build one leaves it. The pair of
    auto-expand answers states which stars the mode opens the way down to, as the reader's preference
    does, and the mode is stated the way a session restores it — so the way down opens once a test
    asks for the mode through :func:`select_favorites`.
    """
    panel = GUISequencerBrowserPanel.__new__(GUISequencerBrowserPanel)
    panel.tag = panel_tag
    panel._state_expansion_memory(set() if expanded_rows is None else expanded_rows)
    panel.tree_tag = TREE_TAG
    panel.tree = corpus.tree
    panel._logic = FakeTreeLogic(  # type: ignore[assignment]
        favorites,
        auto_expand_reconstructions=auto_expand_reconstructions,
        auto_expand_directories=auto_expand_directories,
    )
    panel._language_manager = FakeLanguageManager()
    panel._colors = TREE_COLORS
    _state_detail_labels(panel)
    panel._favorites_checkbox_tag = None
    panel._favorites_glyph_tag = None
    panel.on_favorites_filter_changed = None
    panel._filter = TreeFilter(query=query, favorites_only=favorites_only)
    panel._auto_expand_pending = False
    panel._resolve_filter()
    return panel


def _state_detail_labels(panel: GUITreePanel) -> None:
    """States the labels a row's details read under, which a configuration row asks for by name."""
    panel._lbl_detail_sample_rate = "sample_rate"
    panel._lbl_detail_nes_frequency = "nes_frequency"
    panel._lbl_detail_spectrum_method = "spectrum_method"
    panel._lbl_detail_transformation_gamma = "transformation_gamma"
    panel._lbl_detail_window_size = "window_size"
    panel._lbl_detail_generators = "generators"
    panel._lbl_detail_configuration = "configuration"


def collect_specs(panel: GUITreePanel) -> List[NodeSpec]:
    """Collects the rows a rebuild would emit, which is the pass running off the main thread."""
    panel._node_handlers = {
        node_type: NodeHandler(tag=f"handler.{node_type.value}", node_type=node_type) for node_type in NodeType
    }
    return panel._collect_specs(panel.tree_tag)


def render_view(panel: GUITreePanel) -> str:
    """Renders the view a rebuild would leave on screen: the rows, their nesting and their state.

    Each row reads as its marker and its label, indented under the row holding it: ``v`` a container
    standing open, ``>`` one standing closed, ``-`` a leaf. A row the search hides is marked, since
    its widget stands there either way, and a row under a closed container is rendered where it is.
    """
    children: Dict[str, List[NodeSpec]] = defaultdict(list)
    for spec in collect_specs(panel):
        children[spec.parent_tag].append(spec)

    lines: List[str] = []
    _render_rows(
        panel,
        children,
        parent_tag=panel.tree_tag,
        depth=0,
        lines=lines,
    )
    return "\n".join(lines)


def _render_rows(
    panel: GUITreePanel,
    children: Mapping[str, Sequence[NodeSpec]],
    *,
    parent_tag: str,
    depth: int,
    lines: List[str],
) -> None:
    for spec in children.get(parent_tag, ()):
        lines.append(f"{INDENT * depth}{_row_marker(spec)} {spec.label}{_row_state(panel, spec)}")
        _render_rows(
            panel,
            children,
            parent_tag=spec.node_tag,
            depth=depth + 1,
            lines=lines,
        )


def _row_marker(spec: NodeSpec) -> str:
    if spec.leaf:
        return LEAF_MARKER

    return OPEN_MARKER if spec.should_expand else CLOSED_MARKER


def _row_state(panel: GUITreePanel, spec: NodeSpec) -> str:
    return "" if panel._is_node_visible(spec.node) else HIDDEN_MARKER


def nodes_at(corpus: BrowserCorpus, key: str) -> Tuple[FileSystemNode, ...]:
    """Every row standing for one path, which is what a favorite reaches across the two views."""
    path = corpus.paths[key]
    return corpus.tree.find_nodes(FileSystemNode, lambda node: node.filepath == path)


def row_named(corpus: BrowserCorpus, label: str) -> TreeNode:
    """The row reading under this label, which is how a test names a heading the browser wrote."""
    rows = corpus.tree.find_nodes(TreeNode, lambda node: str(node.name) == label)
    assert len(rows) == 1
    return rows[0]


def set_row_expanded(
    panel: GUITreePanel,
    node: TreeNode,
    *,
    expanded: bool,
) -> None:
    """Leaves a row standing the way the reader would leave it, which the browser then remembers."""
    panel._set_row_expanded(panel._generate_node_tag(node), expanded)


def set_filter(
    panel: GUITreePanel,
    *,
    favorites_only: bool,
    query: str = "",
) -> None:
    """States what the browser is now asked to show, as a change of the control or the search box."""
    panel._filter = TreeFilter(query=query, favorites_only=favorites_only)
    panel._resolve_filter()


def select_favorites(panel: GUITreePanel) -> None:
    """Switches the favorites mode on the way the reader's click does, and resolves the pass it starts.

    Asking to be shown the favorites is what asks the browser to follow a star, so a view showing an
    opened row is read through this rather than through a mode stated any other way.
    """
    panel._state_favorites_only(True)
    panel._resolve_filter()


def deselect_favorites(panel: GUITreePanel) -> None:
    """Switches the favorites mode off the way the reader's click does, and resolves the pass it starts.

    Switching the mode off is what hands back the rows it opened, so a view showing them folded is read
    through this.
    """
    panel._state_favorites_only(False)
    panel._resolve_filter()


def resolve_pass(panel: GUITreePanel) -> None:
    """Resolves the filter afresh, which every pass of a rebuild does before it collects the rows."""
    panel._resolve_filter()


def view(
    corpus: BrowserCorpus,
    favorites: Set[Path],
    *,
    favorites_only: bool,
    query: str = "",
    auto_expand_reconstructions: bool = False,
    auto_expand_directories: bool = False,
) -> str:
    """The view a browser showing the corpus under this filter leaves on screen."""
    return render_view(
        build_browser_panel(
            corpus,
            favorites,
            favorites_only=favorites_only,
            query=query,
            auto_expand_reconstructions=auto_expand_reconstructions,
            auto_expand_directories=auto_expand_directories,
        )
    )


def view_on_selecting_favorites(
    corpus: BrowserCorpus,
    favorites: Set[Path],
    *,
    auto_expand_reconstructions: bool = False,
    auto_expand_directories: bool = False,
) -> str:
    """The view a browser leaves once the reader switches the favorites mode on."""
    panel = build_browser_panel(
        corpus,
        favorites,
        favorites_only=False,
        auto_expand_reconstructions=auto_expand_reconstructions,
        auto_expand_directories=auto_expand_directories,
    )
    select_favorites(panel)
    return render_view(panel)
