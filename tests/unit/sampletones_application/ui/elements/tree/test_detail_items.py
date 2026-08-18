from pathlib import Path
from typing import Final, List

import pytest

from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.panels.sequencer.browser import GUISequencerBrowserPanel
from sampletones_core.configs import Config
from sampletones_core.configs.display import format_frequencies, format_sample_rate, short_hash
from sampletones_core.reconstructions.converter.paths import ConfigDirectoryFields
from sampletones_core.structures.tree.node import (
    ConfigGroupNode,
    ConfigNode,
    FileSystemNode,
    TreeNode,
)
from sampletones_core.structures.tree.type import NodeType
from sampletones_shared.paths.extensions import EXT_FILE_RECONSTRUCTION
from tests.suite.language import FakeLanguageManager

CONFIG_FIELDS: Final[ConfigDirectoryFields] = ConfigDirectoryFields.from_config(Config())
CONFIG_DIRECTORY: Final[Path] = Path("/reconstructions") / CONFIG_FIELDS.directory_name
RECONSTRUCTION_PATH: Final[Path] = CONFIG_DIRECTORY / f"song{EXT_FILE_RECONSTRUCTION}"

DETAIL_LABELS: Final[List[str]] = [
    "sample_rate",
    "nes_frequency",
    "spectrum_method",
    "transformation_gamma",
    "window_size",
    "generators",
    "configuration",
]


@pytest.fixture
def panel() -> GUISequencerBrowserPanel:
    """Builds a browser panel without its DearPyGui-dependent constructor.

    Resolving a node's detail items reads only the language-resolved detail labels, so the pieces
    the constructor would build around a running GUI context are unnecessary here. A concrete
    browser stands in for the base because the configuration font is a browser-level opt-in.
    """
    instance = GUISequencerBrowserPanel.__new__(GUISequencerBrowserPanel)
    instance._language_manager = FakeLanguageManager()
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
