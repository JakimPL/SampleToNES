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
    ConfigNode,
    FileSystemNode,
    NodeType,
    Tree,
    TreeNode,
    create_directory_node,
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
        reconstructions_node = TreeNode(
            name=self._language_manager["global.browser.label.reconstructions"],
            node_type=NodeType.GROUP,
            parent=container_root,
        )
        samples_node = TreeNode(
            name=self._language_manager["global.browser.label.samples"],
            node_type=NodeType.GROUP,
            parent=container_root,
        )

        for path in sorted(self.reconstructions_directory.iterdir()):
            self._build_tree(path, parent=reconstructions_node)

        self._organize_top_level_config_directories(reconstructions_node)
        self._build_samples_children(samples_node)
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

        directory_node = create_directory_node(
            path,
            name=path.name,
            parent=parent,
        )
        for child_node in children_nodes:
            child_node.parent = directory_node

        return directory_node

    def _organize_top_level_config_directories(
        self,
        reconstructions_node: TreeNode,
    ) -> None:
        """Groups top-level config directories under frequencies/method nodes, leaving other folders flat.

        A config directory moves under ``frequencies`` ▶ ``method`` artificial group nodes and is
        renamed to its generator abbreviation, while any other top-level folder keeps the existing
        flat friendly naming for the config directories nested inside it.
        """
        for child in list(reconstructions_node.children):
            match child:
                case ConfigNode() if child.node_type == NodeType.DIRECTORY:
                    self._attach_config_directory_under_groups(
                        child,
                        reconstructions_node,
                    )
                case FileSystemNode() if child.node_type == NodeType.DIRECTORY:
                    self._assign_directory_display_names(child)

        self._disambiguate_generator_siblings(reconstructions_node)

    def _attach_config_directory_under_groups(
        self,
        directory_node: ConfigNode,
        reconstructions_node: TreeNode,
    ) -> None:
        fields = directory_node.config
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
            reconstructions_node,
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
            by_name: Dict[str, List[ConfigNode]] = {}
            for child in node.children:
                if isinstance(child, ConfigNode) and child.node_type == NodeType.DIRECTORY:
                    by_name.setdefault(child.name, []).append(child)

            for name, members in by_name.items():
                if len(members) <= 1:
                    continue

                for directory_node in members:
                    directory_node.name = disambiguated_display_name(name, directory_node.config.ch)

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
        groups: Dict[str, List[ConfigNode]] = {}
        for child in node.children:
            if not isinstance(child, ConfigNode) or child.node_type != NodeType.DIRECTORY:
                continue

            groups.setdefault(child.config.display_name, []).append(child)

        for display_name, members in groups.items():
            if len(members) == 1:
                members[0].name = display_name
                continue

            for directory_node in members:
                directory_node.name = disambiguated_display_name(display_name, directory_node.config.ch)

    def _build_samples_children(self, samples_node: TreeNode) -> None:
        """Populates the transposed Samples branch: source-audio directories ▶ audio ▶ config variants."""
        variants_by_audio: Dict[Tuple[Tuple[str, ...], str], List[Tuple[ConfigDirectoryFields, Path]]] = {}

        for config_directory in sorted(self.reconstructions_directory.iterdir()):
            if not config_directory.is_dir():
                continue

            fields = ConfigDirectoryFields.from_directory_name(config_directory.name)
            if fields is None:
                continue

            for reconstruction_path in sorted(config_directory.rglob(f"*{EXT_FILE_RECONSTRUCTION}")):
                relative = reconstruction_path.relative_to(config_directory)
                audio_key = (relative.parent.parts, relative.stem)
                variants_by_audio.setdefault(audio_key, []).append((fields, reconstruction_path))

        for audio_key in sorted(variants_by_audio):
            directory_parts, audio_name = audio_key
            parent = samples_node
            for part in directory_parts:
                parent = self._find_or_create_group_node(part, parent)

            audio_node = self._find_or_create_group_node(audio_name, parent)
            self._append_config_variants(audio_node, variants_by_audio[audio_key])

    def _append_config_variants(
        self,
        audio_node: TreeNode,
        variants: List[Tuple[ConfigDirectoryFields, Path]],
    ) -> None:
        variants_by_display_name: Dict[str, List[Tuple[ConfigDirectoryFields, Path]]] = {}
        for fields, reconstruction_path in variants:
            variants_by_display_name.setdefault(fields.display_name, []).append((fields, reconstruction_path))

        for display_name, members in variants_by_display_name.items():
            for fields, reconstruction_path in members:
                label = display_name if len(members) == 1 else disambiguated_display_name(display_name, fields.ch)
                ConfigNode(
                    label,
                    node_type=NodeType.FILE,
                    filepath=reconstruction_path,
                    config=fields,
                    parent=audio_node,
                )

    def get_all_reconstruction_files(self) -> List[Path]:
        file_paths = {
            node.filepath
            for node in self.tree.collect_leaves()
            if isinstance(node, FileSystemNode) and node.node_type == NodeType.FILE
        }
        return sorted(file_paths)
