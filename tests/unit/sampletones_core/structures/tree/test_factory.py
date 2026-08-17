from pathlib import Path

from sampletones_core.configs import Config
from sampletones_core.reconstructions.converter.paths import ConfigDirectoryFields
from sampletones_core.structures.tree.factory import create_directory_node
from sampletones_core.structures.tree.node import ConfigNode, FileSystemNode, TreeNode
from sampletones_core.structures.tree.type import NodeType

CONFIG_FIELDS = ConfigDirectoryFields.from_config(Config())
RECONSTRUCTIONS_DIRECTORY = Path("/reconstructions")


class TestCreateDirectoryNode:
    def test_stated_configuration_becomes_a_config_node(self) -> None:
        directory = RECONSTRUCTIONS_DIRECTORY / CONFIG_FIELDS.directory_name
        node = create_directory_node(
            directory,
            name=directory.name,
            config=CONFIG_FIELDS,
            parent=None,
        )
        assert isinstance(node, ConfigNode)
        assert node.config == CONFIG_FIELDS

    def test_folder_stating_no_configuration_becomes_a_file_system_node(self) -> None:
        directory = RECONSTRUCTIONS_DIRECTORY / "my_songs"
        node = create_directory_node(
            directory,
            name=directory.name,
            config=None,
            parent=None,
        )
        assert isinstance(node, FileSystemNode)
        assert not isinstance(node, ConfigNode)

    def test_node_carries_the_given_name_and_path(self) -> None:
        directory = RECONSTRUCTIONS_DIRECTORY / CONFIG_FIELDS.directory_name
        node = create_directory_node(
            directory,
            name="friendly",
            config=CONFIG_FIELDS,
            parent=None,
        )
        assert node.name == "friendly"
        assert node.filepath == directory
        assert node.node_type == NodeType.DIRECTORY

    def test_node_attaches_to_the_given_parent(self) -> None:
        parent = TreeNode("root", NodeType.ROOT)
        node = create_directory_node(
            RECONSTRUCTIONS_DIRECTORY / "my_songs",
            name="my_songs",
            config=None,
            parent=parent,
        )
        assert node.parent is parent
