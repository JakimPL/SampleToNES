from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_core.configs.display import (
    DISPLAY_SEPARATOR,
    GAMMA_PREFIX,
    disambiguated_display_name,
    format_nes_frequency,
    format_sample_rate,
    format_spectrum_method,
)
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
        self._language_manager = language_manager
        self.config_manager = config_manager
        self.reconstructions_directory = config_manager.get_reconstructions_directory()

        self.tree = Tree()

    def set_reconstructions_directory(self, directory: Path) -> None:
        self.reconstructions_directory = directory
        self.refresh_tree()

    def refresh_tree(self) -> None:
        if not self.reconstructions_directory.exists() or not self.reconstructions_directory.is_dir():
            self.tree.set_root(None)
            return

        container_root = TreeNode(
            name=self._language_manager["global.browser.label.root"],
            node_type=NodeType.ROOT,
        )
        for path in sorted(self.reconstructions_directory.iterdir()):
            self._build_tree(path, parent=container_root)

        self._organize_top_level_config_directories(container_root)
        self.tree.set_root(container_root)

    def _build_tree(
        self,
        path: Path,
        parent: Optional[TreeNode] = None,
    ) -> Optional[FileSystemNode]:
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

    def _organize_top_level_config_directories(
        self,
        container_root: TreeNode,
    ) -> None:
        """Groups top-level config directories under frequencies/method nodes, leaving other folders flat.

        A config directory moves under ``frequencies`` ▶ ``method`` artificial group nodes and is
        renamed to its generator abbreviation, while any other top-level folder keeps the existing
        flat friendly naming for the config directories nested inside it.
        """
        for child in list(container_root.children):
            if not isinstance(child, FileSystemNode) or child.node_type != NodeType.DIRECTORY:
                continue

            fields = ConfigDirectoryFields.from_directory_name(child.filepath.name)
            if fields is None:
                self._assign_directory_display_names(child)
                continue

            self._attach_config_directory_under_groups(
                child,
                fields,
                container_root,
            )

        self._disambiguate_generator_siblings(container_root)

    def _attach_config_directory_under_groups(
        self,
        directory_node: FileSystemNode,
        fields: ConfigDirectoryFields,
        container_root: TreeNode,
    ) -> None:
        frequencies_name = DISPLAY_SEPARATOR.join(
            [
                format_sample_rate(fields.sr),
                format_nes_frequency(fields.nf),
            ]
        )
        method_name = DISPLAY_SEPARATOR.join(
            [
                format_spectrum_method(fields.sm),
                f"{GAMMA_PREFIX}{fields.tg}",
            ]
        )
        frequencies_node = self._find_or_create_group_node(
            frequencies_name,
            container_root,
        )
        method_node = self._find_or_create_group_node(
            method_name,
            frequencies_node,
        )

        directory_node.name = fields.gn
        directory_node.parent = method_node

    def _find_or_create_group_node(
        self,
        name: str,
        parent: TreeNode,
    ) -> TreeNode:
        for child in parent.children:
            if isinstance(child, TreeNode) and child.node_type == NodeType.GROUP and child.name == name:
                return child

        return TreeNode(name, node_type=NodeType.GROUP, parent=parent)

    def _disambiguate_generator_siblings(self, node: TreeNode) -> None:
        """Appends a short config hash to generator leaves that share a name under one method group."""
        if node.node_type == NodeType.GROUP:
            by_name: Dict[str, List[FileSystemNode]] = {}
            for child in node.children:
                if isinstance(child, FileSystemNode) and child.node_type == NodeType.DIRECTORY:
                    by_name.setdefault(child.name, []).append(child)

            for name, members in by_name.items():
                if len(members) <= 1:
                    continue

                for directory_node in members:
                    fields = ConfigDirectoryFields.from_directory_name(directory_node.filepath.name)
                    if fields is not None:
                        directory_node.name = disambiguated_display_name(name, fields.ch)

        for child in node.children:
            self._disambiguate_generator_siblings(child)

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
                directory_node.name = disambiguated_display_name(display_name, fields.ch)

    def get_all_reconstruction_files(self) -> List[Path]:
        file_nodes = [
            node
            for node in self.tree.collect_leaves()
            if isinstance(node, FileSystemNode) and node.node_type == NodeType.FILE
        ]
        return [node.filepath for node in file_nodes]
