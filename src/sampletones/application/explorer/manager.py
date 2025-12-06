from pathlib import Path
from typing import Dict, Optional

from sampletones.constants.paths import (
    EXT_FILE_LIBRARY,
    EXT_FILE_RECONSTRUCTION,
    EXT_FILE_WAVE,
)
from sampletones.tree import FileSystemNode, Tree

from ..constants import NOD_TYPE_DIRECTORY, NOD_TYPE_FILE


class ExplorerManager:
    def __init__(self, root_directory: Optional[Path] = None) -> None:
        self.tree = Tree()
        self.root_directory = root_directory or Path.cwd()
        self._expanded_directories: Dict[Path, bool] = {}

    def set_root_directory(self, directory: Path) -> None:
        self.root_directory = directory
        self._expanded_directories.clear()
        self.refresh_tree()

    def refresh_tree(self) -> None:
        if not self.root_directory.exists() or not self.root_directory.is_dir():
            self.tree.set_root(None)
            return

        root_node = self._create_directory_node(self.root_directory, load_children=True)
        self.tree.set_root(root_node)

    def _create_directory_node(
        self,
        directory_path: Path,
        load_children: bool = False,
    ) -> FileSystemNode:
        node = FileSystemNode(
            name=directory_path.name or str(directory_path),
            filepath=directory_path,
            node_type=NOD_TYPE_DIRECTORY,
        )

        if load_children:
            self._load_directory_children(node)

        return node

    def _load_directory_children(self, directory_node: FileSystemNode) -> None:
        directory_path = directory_node.filepath
        if not directory_path.is_dir():
            return

        self._expanded_directories[directory_path] = True
        for existing_child in list(directory_node.children):
            existing_child.parent = None

        try:
            entries = sorted(directory_path.iterdir(), key=lambda path: (not path.is_dir(), path.name.lower()))
        except (PermissionError, OSError):
            return

        for entry_path in entries:
            try:
                if entry_path.is_dir():
                    FileSystemNode(
                        name=entry_path.name,
                        filepath=entry_path,
                        node_type=NOD_TYPE_DIRECTORY,
                        parent=directory_node,
                    )
                elif entry_path.is_file():
                    if entry_path.suffix.lower() in [
                        EXT_FILE_WAVE,
                        EXT_FILE_LIBRARY,
                        EXT_FILE_RECONSTRUCTION,
                    ]:
                        FileSystemNode(
                            name=entry_path.name,
                            filepath=entry_path,
                            node_type=NOD_TYPE_FILE,
                            parent=directory_node,
                        )
            except (PermissionError, OSError):
                continue

    def expand_directory(self, directory_node: FileSystemNode) -> None:
        if directory_node.node_type != NOD_TYPE_DIRECTORY:
            return

        directory_path = directory_node.filepath

        if self.is_directory_expanded(directory_path):
            return

        self._load_directory_children(directory_node)

    def is_directory_expanded(self, directory_path: Path) -> bool:
        return self._expanded_directories.get(directory_path, False)

    def collapse_directory(self, directory_path: Path) -> None:
        if directory_path in self._expanded_directories:
            del self._expanded_directories[directory_path]
