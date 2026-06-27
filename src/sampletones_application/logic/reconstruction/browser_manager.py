from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sampletones_application.categories.elements.global_ import TreeElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_core.configs.display import DISPLAY_SEPARATOR, short_hash
from sampletones_core.paths import EXT_FILE_RECONSTRUCTION
from sampletones_core.reconstructions.converter.paths import ConfigDirectoryFields
from sampletones_core.structures.tree import (
    FileSystemNode,
    NodeType,
    Tree,
    TreeNode,
)


class BrowserManager:
    def __init__(
        self,
        config_manager: ConfigManager,
        *,
        language_manager: LanguageManager,
    ) -> None:
        self.config_manager = config_manager
        self.reconstructions_directory = config_manager.get_reconstructions_directory()
        self._root_label = language_manager[
            Page.GLOBAL,
            Panel.BROWSER,
            TextType.LABEL,
            TreeElements.ROOT,
        ]

        self.tree = Tree()

    def set_reconstructions_directory(self, directory: Path) -> None:
        self.reconstructions_directory = directory
        self.refresh_tree()

    def refresh_tree(self) -> None:
        if not self.reconstructions_directory.exists() or not self.reconstructions_directory.is_dir():
            self.tree.set_root(None)
            return

        container_root = TreeNode(
            name=self._root_label,
            node_type=NodeType.ROOT,
        )
        for path in sorted(self.reconstructions_directory.iterdir()):
            self._build_tree(path, parent=container_root)

        self._assign_directory_display_names(container_root)
        self.tree.set_root(container_root)

    def _build_tree(self, path: Path, parent: Optional[TreeNode] = None) -> Optional[FileSystemNode]:
        if not path.exists():
            return None

        if path.is_file():
            if path.suffix == EXT_FILE_RECONSTRUCTION:
                return FileSystemNode(
                    path.stem,
                    filepath=path,
                    node_type=NodeType.FILE,
                    parent=parent,
                )
            return None

        children_nodes = []
        for child_path in sorted(path.iterdir()):
            child_node = self._build_tree(child_path, parent=parent)
            if child_node is not None:
                children_nodes.append(child_node)

        directory_node = FileSystemNode(
            path.name,
            filepath=path,
            node_type=NodeType.DIRECTORY,
            parent=parent,
        )
        for child_node in children_nodes:
            child_node.parent = directory_node

        return directory_node

    def _assign_directory_display_names(self, node: TreeNode) -> None:
        """Renames config-directory nodes to friendly labels, disambiguating colliding siblings.

        Only directories whose names parse as reconstruction config directories are rewritten;
        plain folders keep their on-disk name. The check is scoped per parent because duplicate
        display names among siblings would otherwise collapse to duplicate widget tags downstream.
        """
        self._rename_config_directory_children(node)
        for child in node.children:
            self._assign_directory_display_names(child)

    def _rename_config_directory_children(self, node: TreeNode) -> None:
        groups: Dict[str, List[Tuple[FileSystemNode, ConfigDirectoryFields]]] = {}
        for child in node.children:
            if not isinstance(child, FileSystemNode) or child.node_type != NodeType.DIRECTORY:
                continue

            fields = ConfigDirectoryFields.from_directory_name(child.filepath.name)
            if fields is None:
                continue

            groups.setdefault(fields.display_name, []).append((child, fields))

        for display_name, members in groups.items():
            if len(members) == 1:
                directory_node, _ = members[0]
                directory_node.name = display_name
                continue

            for directory_node, fields in members:
                directory_node.name = f"{display_name}{DISPLAY_SEPARATOR}#{short_hash(fields.config_hash)}"

    def get_all_reconstruction_files(self) -> List[Path]:
        file_nodes = [
            node
            for node in self.tree.collect_leaves()
            if isinstance(node, FileSystemNode) and node.node_type == NodeType.FILE
        ]
        return [node.filepath for node in file_nodes]
