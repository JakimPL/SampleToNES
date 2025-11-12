from pathlib import Path
from typing import Dict, Optional

from sampletones.constants.general import EXT_FILE_JSON
from sampletones.tree import FileSystemNode, Tree

from ..constants import NOD_TYPE_DIRECTORY, NOD_TYPE_FILE
from ..reconstruction.data import ReconstructionData


class BrowserManager:
    def __init__(self, output_directory: Path) -> None:
        self.output_directory = output_directory
        self.tree = Tree()
        self.file_cache: Dict[Path, Optional[ReconstructionData]] = {}

    def set_output_directory(self, directory: Path) -> None:
        self.output_directory = directory
        self.refresh_tree()

    def refresh_tree(self) -> None:
        if not self.output_directory.exists() or not self.output_directory.is_dir():
            self.tree.set_root(None)
            return

        root = self._build_tree(self.output_directory)
        self.tree.set_root(root)

    def _build_tree(self, path: Path) -> Optional[FileSystemNode]:
        if not path.exists():
            return None

        if path.is_file():
            if path.suffix == EXT_FILE_JSON:
                return FileSystemNode(path.stem, filepath=path, node_type=NOD_TYPE_FILE)
            return None

        children_nodes = []
        for child_path in sorted(path.iterdir()):
            child_node = self._build_tree(child_path)
            if child_node is not None:
                children_nodes.append(child_node)

        if not children_nodes:
            return None

        directory_node = FileSystemNode(path.name, filepath=path, node_type=NOD_TYPE_DIRECTORY)

        for child_node in children_nodes:
            child_node.parent = directory_node

        return directory_node

    def load_reconstruction_data(self, filepath: Path) -> ReconstructionData:
        if filepath in self.file_cache:
            cached_data = self.file_cache[filepath]
            if cached_data is not None:
                return cached_data

        if filepath.is_dir():
            raise IsADirectoryError(f"Expected a file but got a directory: {filepath}")

        if not filepath.exists():
            raise FileNotFoundError(f"Reconstruction file not found: {filepath}")

        data = ReconstructionData.load(filepath)
        self.file_cache[filepath] = data
        return data

    def get_all_reconstruction_files(self) -> list[Path]:
        file_nodes = [node for node in self.tree.collect_leaves() if isinstance(node, FileSystemNode)]
        return [node.filepath for node in file_nodes if node.filepath is not None]

    def clear_cache(self) -> None:
        self.file_cache.clear()
