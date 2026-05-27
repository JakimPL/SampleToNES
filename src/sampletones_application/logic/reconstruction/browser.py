from pathlib import Path
from typing import List, Optional

from sampletones_application.config.manager import ConfigManager
from sampletones_application.constants.general import LBL_TREE_ROOT
from sampletones_core.constants.paths import EXT_FILE_RECONSTRUCTION
from sampletones_core.structures.tree import FileSystemNode, NodeType, Tree, TreeNode


class BrowserManager:
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager
        self.output_directory = config_manager.get_output_directory()

        self.tree = Tree()

    def set_output_directory(self, directory: Path) -> None:
        self.output_directory = directory
        self.refresh_tree()

    def refresh_tree(self) -> None:
        if not self.output_directory.exists() or not self.output_directory.is_dir():
            self.tree.set_root(None)
            return

        container_root = TreeNode(name=LBL_TREE_ROOT, node_type=NodeType.ROOT)
        for path in sorted(self.output_directory.iterdir()):
            self._build_tree(path, parent=container_root)

        self.tree.set_root(container_root)

    def _build_tree(self, path: Path, parent: Optional[TreeNode] = None) -> Optional[FileSystemNode]:
        if not path.exists():
            return None

        if path.is_file():
            if path.suffix == EXT_FILE_RECONSTRUCTION:
                return FileSystemNode(path.stem, filepath=path, node_type=NodeType.FILE, parent=parent)
            return None

        children_nodes = []
        for child_path in sorted(path.iterdir()):
            child_node = self._build_tree(child_path, parent=parent)
            if child_node is not None:
                children_nodes.append(child_node)

        directory_node = FileSystemNode(path.name, filepath=path, node_type=NodeType.DIRECTORY, parent=parent)
        for child_node in children_nodes:
            child_node.parent = directory_node

        return directory_node

    def get_all_reconstruction_files(self) -> List[Path]:
        file_nodes = [node for node in self.tree.collect_leaves() if isinstance(node, FileSystemNode)]
        return [node.filepath for node in file_nodes]
