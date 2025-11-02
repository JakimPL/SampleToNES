from pathlib import Path
from typing import Dict, List, Optional

from browser.browser.node import ReconstructionNode
from constants.general import OUTPUT_DIRECTORY
from reconstructor.reconstruction import Reconstruction


class BrowserManager:
    def __init__(self, output_directory: str = OUTPUT_DIRECTORY) -> None:
        self.output_directory = output_directory
        self.tree: Optional[ReconstructionNode] = None
        self.file_cache: Dict[Path, Optional[Reconstruction]] = {}

    def set_output_directory(self, directory: str) -> None:
        self.output_directory = directory
        self.refresh_tree()

    def refresh_tree(self) -> None:
        output_path = Path(self.output_directory)
        if not output_path.exists() or not output_path.is_dir():
            self.tree = None
            return

        self.tree = self._build_tree(output_path)

    def get_tree(self) -> Optional[ReconstructionNode]:
        if self.tree is None:
            self.refresh_tree()

        return self.tree

    def _build_tree(self, path: Path) -> Optional[ReconstructionNode]:
        if not path.exists():
            return None

        if path.is_file():
            if path.suffix == ".json":
                return ReconstructionNode(name=path.stem, path=path, is_file=True, children=[])
            return None

        children = []
        for child_path in sorted(path.iterdir()):
            child_node = self._build_tree(child_path)
            if child_node is not None:
                children.append(child_node)

        if not children:
            return None

        return ReconstructionNode(name=path.name, path=path, is_file=False, children=children)

    def load_reconstruction_data(self, file_path: Path) -> Reconstruction:
        if file_path in self.file_cache:
            cached_data = self.file_cache[file_path]
            if cached_data is not None:
                return cached_data

        if not self.validate_reconstruction_file(file_path):
            raise ValueError(f"Invalid reconstruction file: {file_path}")

        data = Reconstruction.load(file_path)
        self.file_cache[file_path] = data
        return data

    def validate_reconstruction_file(self, file_path: Path) -> bool:
        # TODO: Proper validation logic
        return file_path.suffix == ".json" and file_path.exists()

    def get_all_reconstruction_files(self) -> List[Path]:
        if self.tree is None:
            self.refresh_tree()

        if self.tree is None:
            return []

        return self._collect_files(self.tree)

    def clear_cache(self) -> None:
        self.file_cache.clear()

    def _collect_files(self, node: ReconstructionNode) -> List[Path]:
        files = []
        if node.is_file:
            files.append(node.path)
        else:
            for child in node.children:
                files.extend(self._collect_files(child))

        return files
