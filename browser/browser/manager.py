from pathlib import Path
from typing import Dict, Optional

from browser.reconstruction.data import ReconstructionData
from browser.tree.node import FileSystemNode, TreeNode
from browser.tree.tree import Tree
from constants.browser import EXT_RECONSTRUCTION_FILE, NOD_TYPE_DIRECTORY, NOD_TYPE_FILE
from constants.general import OUTPUT_DIRECTORY


class BrowserManager:
    def __init__(self, output_directory: str = OUTPUT_DIRECTORY) -> None:
        self.output_directory = output_directory
        self.tree = Tree()
        self.file_cache: Dict[Path, Optional[ReconstructionData]] = {}

    def set_output_directory(self, directory: str) -> None:
        self.output_directory = directory
        self.refresh_tree()

    def refresh_tree(self) -> None:
        output_path = Path(self.output_directory)
        if not output_path.exists() or not output_path.is_dir():
            self.tree.set_root(None)
            return

        root = self._build_tree(output_path)
        self.tree.set_root(root)

    def _build_tree(self, path: Path) -> Optional[FileSystemNode]:
        if not path.exists():
            return None

        if path.is_file():
            if path.suffix == EXT_RECONSTRUCTION_FILE:
                return FileSystemNode(path.stem, file_path=path, node_type=NOD_TYPE_FILE)
            return None

        children_nodes = []
        for child_path in sorted(path.iterdir()):
            child_node = self._build_tree(child_path)
            if child_node is not None:
                children_nodes.append(child_node)

        if not children_nodes:
            return None

        directory_node = FileSystemNode(path.name, file_path=path, node_type=NOD_TYPE_DIRECTORY)

        for child_node in children_nodes:
            child_node.parent = directory_node

        return directory_node

    def load_reconstruction_data(self, file_path: Path) -> ReconstructionData:
        if file_path in self.file_cache:
            cached_data = self.file_cache[file_path]
            if cached_data is not None:
                return cached_data

        if not self.validate_reconstruction_file(file_path):
            raise ValueError(f"Invalid reconstruction file: {file_path}")

        data = ReconstructionData.load(file_path)
        self.file_cache[file_path] = data
        return data

    def validate_reconstruction_file(self, file_path: Path) -> bool:
        return file_path.suffix == EXT_RECONSTRUCTION_FILE and file_path.exists()

    def get_all_reconstruction_files(self) -> list[Path]:
        file_nodes = [
            node
            for node in self.tree.collect_leaves()
            if isinstance(node, FileSystemNode) and node.node_type == NOD_TYPE_FILE
        ]
        return [node.file_path for node in file_nodes if node.file_path is not None]

    def clear_cache(self) -> None:
        self.file_cache.clear()
