from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, TypeVar

from anytree import Node

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.library import InstructionLibraryKey
from sampletones_core.reconstructions.converter.paths import ConfigDirectoryFields

from .type import NodeType

TreeNodeT = TypeVar("TreeNodeT", bound="TreeNode")


class TreeNode(Node):
    """A node of one of the application's trees, and the base every node kind derives from.

    ``anytree`` lets a tree hold nodes of any type, so it states a node's relatives as untyped.
    Every tree here is built from this class alone, which is what these declarations state: a
    relative of a node is a node of ours, and the checker holds each reader to the attributes the
    node kind it reached actually carries.

    ``gathered_plain_name`` says that the node's name has taken in a name somebody chose — a
    folder's, an audio file's — which a tree hands a row when it folds a heading into it. The
    classes naming a configuration read it through :attr:`states_configuration`, so a reader of
    configuration text meets the row as the plain name it has become.
    """

    name: str
    parent: Optional[TreeNode]
    children: Tuple[TreeNode, ...]
    path: Tuple[TreeNode, ...]
    root: TreeNode
    ancestors: Tuple[TreeNode, ...]
    descendants: Tuple[TreeNode, ...]

    def __init__(
        self,
        name: str,
        node_type: NodeType,
        parent: Optional[TreeNode] = None,
    ) -> None:
        super().__init__(name, parent=parent)
        self.node_type = node_type
        self.gathered_plain_name = False

    @property
    def states_configuration(self) -> bool:
        """Whether the node's name is the machine text a reconstruction configuration carries."""
        return False

    def copy(self, parent: Optional[TreeNode] = None) -> TreeNode:
        return self._carrying(TreeNode(self.name, node_type=self.node_type, parent=parent))

    def _carrying(self, node: TreeNodeT) -> TreeNodeT:
        """The fresh node, given what its name has come to hold beside the fields it was built with."""
        node.gathered_plain_name = self.gathered_plain_name
        return node


class FileSystemNode(TreeNode):
    def __init__(
        self,
        name: str,
        node_type: NodeType,
        filepath: Path,
        parent: Optional[TreeNode] = None,
    ) -> None:
        super().__init__(name, node_type=node_type, parent=parent)
        self.filepath = filepath

    def copy(self, parent: Optional[TreeNode] = None) -> FileSystemNode:
        return self._carrying(
            FileSystemNode(
                self.name,
                filepath=self.filepath,
                node_type=self.node_type,
                parent=parent,
            )
        )


class ConfigNode(FileSystemNode):
    """A filesystem node belonging to a reconstruction configuration, carrying the parsed fields.

    A configuration directory encodes its fields in its name, and both the directory itself and the
    reconstructions inside it are read as belonging to that configuration. Holding the parsed
    :class:`ConfigDirectoryFields` on the node lets every reader — labels, tooltips, fonts — state
    the configuration from the node it already has, whatever the node's own filename says.
    """

    def __init__(
        self,
        name: str,
        node_type: NodeType,
        filepath: Path,
        config: ConfigDirectoryFields,
        parent: Optional[TreeNode] = None,
    ) -> None:
        super().__init__(
            name,
            node_type=node_type,
            filepath=filepath,
            parent=parent,
        )
        self.config = config

    @property
    def states_configuration(self) -> bool:
        return not self.gathered_plain_name

    def copy(self, parent: Optional[TreeNode] = None) -> ConfigNode:
        return self._carrying(
            ConfigNode(
                self.name,
                node_type=self.node_type,
                filepath=self.filepath,
                config=self.config,
                parent=parent,
            )
        )


class ConfigGroupNode(TreeNode):
    """A heading gathering the configurations that share a stretch of their display name.

    The browser lifts a configuration directory under the rates it runs at and the spectrum it was
    built from, naming each heading with that stretch of the configuration's own display name.
    Carrying the heading as a class of its own lets a reader of configuration text — a label, a
    tooltip, a font — reach it the way it reaches the configuration row below.
    """

    @property
    def states_configuration(self) -> bool:
        return not self.gathered_plain_name

    def copy(self, parent: Optional[TreeNode] = None) -> ConfigGroupNode:
        return self._carrying(ConfigGroupNode(self.name, node_type=self.node_type, parent=parent))


class LibraryNode(TreeNode):
    """A library file of the catalog, marked ``outdated`` where another version built it."""

    def __init__(
        self,
        name: str,
        library_key: InstructionLibraryKey,
        *,
        outdated: bool,
        node_type: NodeType = NodeType.LIBRARY,
        parent: Optional[TreeNode] = None,
    ) -> None:
        super().__init__(name, node_type=node_type, parent=parent)
        self.library_key = library_key
        self.outdated = outdated

    @property
    def states_configuration(self) -> bool:
        return not self.gathered_plain_name

    def copy(self, parent: Optional[TreeNode] = None) -> LibraryNode:
        return self._carrying(
            LibraryNode(
                self.name,
                node_type=self.node_type,
                library_key=self.library_key,
                outdated=self.outdated,
                parent=parent,
            )
        )


class GeneratorNode(TreeNode):
    def __init__(
        self,
        name: str,
        generator_name: GeneratorName,
        node_type: NodeType = NodeType.GENERATOR,
        parent: Optional[TreeNode] = None,
    ) -> None:
        super().__init__(name, node_type=node_type, parent=parent)
        self.generator_name = generator_name

    def copy(self, parent: Optional[TreeNode] = None) -> GeneratorNode:
        return self._carrying(
            GeneratorNode(
                self.name,
                node_type=self.node_type,
                generator_name=self.generator_name,
                parent=parent,
            )
        )
