from pathlib import Path
from typing import Final, List, Tuple

import pytest

from sampletones_application.layout.general.colors.stem import StemColors
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.panels.sequencer.browser import GUISequencerBrowserPanel
from sampletones_application.utils.palette.colors.literal import LiteralColor
from sampletones_core.configs import Config
from sampletones_core.configs.display import format_frequencies, format_sample_rate, short_hash
from sampletones_core.constants.enums import DEFAULT_CHANNELS
from sampletones_core.reconstructions.converter.paths import ConfigDirectoryFields
from sampletones_core.structures.tree.node import (
    ConfigGroupNode,
    ConfigNode,
    FileSystemNode,
    TreeNode,
)
from sampletones_core.structures.tree.type import NodeType
from sampletones_shared.paths.extensions import EXT_FILE_RECONSTRUCTION
from sampletones_shared.types.application import ColorRGBA
from tests.suite.language import FakeLanguageManager

CONFIG_FIELDS: Final[ConfigDirectoryFields] = ConfigDirectoryFields.from_config(Config(), frozenset(DEFAULT_CHANNELS))
CONFIG_DIRECTORY: Final[Path] = Path("/reconstructions") / CONFIG_FIELDS.directory_name
RECONSTRUCTION_PATH: Final[Path] = CONFIG_DIRECTORY / f"song{EXT_FILE_RECONSTRUCTION}"

DETAIL_LABELS: Final[List[str]] = [
    "sample_rate",
    "nes_frequency",
    "spectrum_method",
    "transformation_gamma",
    "window_size",
    "channels",
    "configuration",
    "stems",
]

RECORDING_COLORS: Final[Tuple[ColorRGBA, ...]] = (
    (200, 80, 40, 255),
    (80, 160, 220, 255),
)
AUTHORED_COLOR: Final[ColorRGBA] = (180, 140, 240, 255)
REST_COLOR: Final[ColorRGBA] = (40, 40, 48, 255)
LEFT_OUT_FRACTION: Final[float] = 0.4

RECORDINGS: Final[Tuple[str, ...]] = ("Drums", "Bass")
ONE_RECORDING: Final[Tuple[str, ...]] = ("Neurostem",)


@pytest.fixture
def stem_colors() -> StemColors:
    return StemColors(
        recordings=tuple(LiteralColor(value) for value in RECORDING_COLORS),
        authored=LiteralColor(AUTHORED_COLOR),
        rest=LiteralColor(REST_COLOR),
        left_out_fraction=LEFT_OUT_FRACTION,
    )


@pytest.fixture
def panel(stem_colors: StemColors) -> GUISequencerBrowserPanel:
    """Builds a browser panel without its DearPyGui-dependent constructor.

    Resolving a node's detail items reads only the language-resolved detail labels, the colors a
    recording is known by and what the panel holds about the row under the pointer, so the pieces
    the constructor would build around a running GUI context are unnecessary here. A concrete
    browser stands in for the base because the configuration font is a browser-level opt-in.
    """
    instance = GUISequencerBrowserPanel.__new__(GUISequencerBrowserPanel)
    instance._language_manager = FakeLanguageManager()
    instance._stem_colors = stem_colors
    instance._detail_document = None
    instance._detail_recordings = ()
    instance._detail_tooltip_owner_tag = None
    instance.on_recordings_requested = None
    for label in DETAIL_LABELS:
        setattr(instance, f"_lbl_detail_{label}", label)

    return instance


def config_directory_node() -> ConfigNode:
    return ConfigNode(
        CONFIG_FIELDS.gn,
        node_type=NodeType.DIRECTORY,
        filepath=CONFIG_DIRECTORY,
        config=CONFIG_FIELDS,
    )


def config_group_node() -> ConfigGroupNode:
    return ConfigGroupNode(
        format_frequencies(CONFIG_FIELDS.sr, CONFIG_FIELDS.nf),
        node_type=NodeType.GROUP,
    )


def plain_directory_node() -> FileSystemNode:
    return FileSystemNode(
        "my_songs",
        node_type=NodeType.DIRECTORY,
        filepath=Path("/reconstructions/my_songs"),
    )


def config_variant_node() -> ConfigNode:
    return ConfigNode(
        CONFIG_FIELDS.display_name,
        node_type=NodeType.FILE,
        filepath=RECONSTRUCTION_PATH,
        config=CONFIG_FIELDS,
    )


def reconstruction_file_node(parent: TreeNode) -> FileSystemNode:
    """A reconstruction as the configuration branch lists it: a file under the folder holding it."""
    return FileSystemNode(
        "song",
        node_type=NodeType.FILE,
        filepath=RECONSTRUCTION_PATH,
        parent=parent,
    )


class TestConfigDetailItems:
    def test_config_directory_states_its_configuration(
        self,
        panel: GUISequencerBrowserPanel,
    ) -> None:
        items = dict(panel._node_detail_items(config_directory_node()))
        assert items["sample_rate"] == format_sample_rate(CONFIG_FIELDS.sr)
        assert items["configuration"] == short_hash(CONFIG_FIELDS.ch)

    def test_config_variant_leaf_states_the_same_configuration(
        self,
        panel: GUISequencerBrowserPanel,
    ) -> None:
        """A reconstruction listed by its configuration answers with that configuration.

        In the sample view a leaf carries the configuration its directory names, which its own
        filename says nothing about.
        """
        assert panel._node_detail_items(config_variant_node()) == panel._node_detail_items(config_directory_node())

    def test_plain_directory_states_nothing(
        self,
        panel: GUISequencerBrowserPanel,
    ) -> None:
        assert panel._node_detail_items(plain_directory_node()) == []

    def test_group_states_nothing(
        self,
        panel: GUISequencerBrowserPanel,
    ) -> None:
        assert panel._node_detail_items(TreeNode("Samples", NodeType.GROUP)) == []


class TestAReconstructionFileRow:
    def test_it_states_the_configuration_of_the_directory_holding_it(
        self,
        panel: GUISequencerBrowserPanel,
    ) -> None:
        """A configuration states its fields in a directory name, which the file inherits by sitting there."""
        directory = config_directory_node()

        items = panel._node_detail_items(reconstruction_file_node(directory))

        assert items == panel._node_detail_items(directory)

    def test_a_file_outside_every_configuration_directory_states_none(
        self,
        panel: GUISequencerBrowserPanel,
    ) -> None:
        assert panel._node_detail_items(reconstruction_file_node(plain_directory_node())) == []


class TestTheRecordingsARowLists:
    def test_a_row_naming_a_document_asks_what_it_holds(
        self,
        panel: GUISequencerBrowserPanel,
    ) -> None:
        asked: List[Path] = []
        panel.on_recordings_requested = asked.append

        panel._node_detail_recordings(config_variant_node())

        assert asked == [RECONSTRUCTION_PATH]

    def test_a_row_naming_no_document_asks_for_nothing(
        self,
        panel: GUISequencerBrowserPanel,
    ) -> None:
        asked: List[Path] = []
        panel.on_recordings_requested = asked.append

        assert panel._node_detail_recordings(config_directory_node()) == ()
        assert asked == []

    def test_the_recordings_read_in_record_order(
        self,
        panel: GUISequencerBrowserPanel,
    ) -> None:
        panel._node_detail_recordings(config_variant_node())
        panel.update_recordings(RECONSTRUCTION_PATH, RECORDINGS)

        swatches = panel._node_detail_recordings(config_variant_node())

        assert tuple(swatch.name for swatch in swatches) == RECORDINGS

    def test_each_recording_takes_the_color_of_the_place_it_holds(
        self,
        panel: GUISequencerBrowserPanel,
        stem_colors: StemColors,
    ) -> None:
        panel._node_detail_recordings(config_variant_node())
        panel.update_recordings(RECONSTRUCTION_PATH, RECORDINGS)

        swatches = panel._node_detail_recordings(config_variant_node())

        assert [swatch.color.rgba for swatch in swatches] == [
            stem_colors.for_position(position).rgba for position in range(len(RECORDINGS))
        ]

    def test_a_document_naming_one_recording_lists_nothing(
        self,
        panel: GUISequencerBrowserPanel,
    ) -> None:
        """One recording says what the row already says, so the list is left to the documents holding several."""
        panel._node_detail_recordings(config_variant_node())
        panel.update_recordings(RECONSTRUCTION_PATH, ONE_RECORDING)

        assert panel._node_detail_recordings(config_variant_node()) == ()

    def test_a_reading_of_another_document_is_left_where_it_is(
        self,
        panel: GUISequencerBrowserPanel,
    ) -> None:
        panel._node_detail_recordings(config_variant_node())

        panel.update_recordings(CONFIG_DIRECTORY / f"other{EXT_FILE_RECONSTRUCTION}", RECORDINGS)

        assert panel._node_detail_recordings(config_variant_node()) == ()


class TestConfigurationFont:
    """Every row whose label is configuration text reads in one font, whatever kind of row it is."""

    def test_config_directory_reads_in_the_configuration_font(
        self,
        panel: GUISequencerBrowserPanel,
    ) -> None:
        assert panel._resolve_node_name_font(config_directory_node()) == Font.MONO_SMALL

    def test_config_variant_leaf_reads_in_the_configuration_font(
        self,
        panel: GUISequencerBrowserPanel,
    ) -> None:
        assert panel._resolve_node_name_font(config_variant_node()) == Font.MONO_SMALL

    def test_configuration_heading_reads_in_the_configuration_font(
        self,
        panel: GUISequencerBrowserPanel,
    ) -> None:
        """A heading gathers a stretch of the configuration, so it reads as the rows below it do."""
        assert panel._resolve_node_name_font(config_group_node()) == Font.MONO_SMALL

    def test_plain_directory_reads_in_the_name_font(
        self,
        panel: GUISequencerBrowserPanel,
    ) -> None:
        assert panel._resolve_node_name_font(plain_directory_node()) == Font.REGULAR_SMALL

    def test_heading_the_disk_names_reads_in_the_name_font(
        self,
        panel: GUISequencerBrowserPanel,
    ) -> None:
        assert panel._resolve_node_name_font(TreeNode("Amen Breaks", NodeType.GROUP)) == Font.REGULAR_SMALL

    def test_row_gathering_a_plain_name_reads_in_the_name_font(
        self,
        panel: GUISequencerBrowserPanel,
    ) -> None:
        """A sample folded into its one variant hands the row an audio's name, which reads as such."""
        variant = config_variant_node()
        variant.gathered_plain_name = True

        assert panel._resolve_node_name_font(variant) == Font.REGULAR_SMALL
