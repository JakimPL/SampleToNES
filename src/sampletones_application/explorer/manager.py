from pathlib import Path
from typing import Dict, List, Optional

from sampletones_core.constants.paths import EXT_FILE_LIBRARY, EXT_FILE_RECONSTRUCTION, EXT_FILES_AUDIO
from sampletones_core.structures.tree import FileSystemNode, NodeType, Tree, TreeNode
from sampletones_shared.utils.system.system import System

from ..config.manager import ConfigManager
from ..constants.general import LBL_TREE_ROOT


class ExplorerManager:
    def __init__(
        self,
        config_manager: ConfigManager,
        depth: int = 0,
    ) -> None:
        self.tree = Tree()
        self.config_manager = config_manager

        self._expanded_directories: Dict[Path, bool] = {}
        self.depth = depth

    def refresh_tree(self) -> None:
        container_root = TreeNode(name=LBL_TREE_ROOT, node_type=NodeType.ROOT)

        filesystems = self._get_filesystems()
        for filesystem_path in filesystems:
            filesystem_node = self._create_directory_node(filesystem_path, parent=container_root)

            selected_path = self._get_ancestor_of_selected(filesystem_path)
            if selected_path is not None:
                self._expand_path_to_selected(filesystem_node, selected_path)

        self.tree.set_root(container_root)

    def _create_directory_node(
        self,
        directory_path: Path,
        parent: Optional[TreeNode] = None,
    ) -> FileSystemNode:
        node = FileSystemNode(
            name=directory_path.name or str(directory_path),
            filepath=directory_path,
            node_type=NodeType.DIRECTORY,
            parent=parent,
        )

        self._load_directory_children(node)
        return node

    def _load_directory_children(
        self,
        directory_node: FileSystemNode,
        level: int = 0,
    ) -> None:
        directory_path = directory_node.filepath
        if not directory_path.is_dir():
            return

        self._expanded_directories[directory_path] = level == 0
        for existing_child in list(directory_node.children):
            existing_child.parent = None

        try:
            entries = sorted(directory_path.iterdir(), key=lambda path: (not path.is_dir(), path.name.lower()))
        except (PermissionError, OSError):
            return

        for entry_path in entries:
            try:
                if entry_path.is_dir():
                    if entry_path.name.startswith("."):
                        continue

                    child_node = FileSystemNode(
                        name=entry_path.name,
                        filepath=entry_path,
                        node_type=NodeType.DIRECTORY,
                        parent=directory_node,
                    )
                    if level < self.depth:
                        self._load_directory_children(
                            child_node,
                            level=level + 1,
                        )
                elif entry_path.is_file():
                    if entry_path.suffix.lower() in [
                        *EXT_FILES_AUDIO,
                        EXT_FILE_LIBRARY,
                        EXT_FILE_RECONSTRUCTION,
                    ]:
                        FileSystemNode(
                            name=entry_path.name,
                            filepath=entry_path,
                            node_type=NodeType.FILE,
                            parent=directory_node,
                        )
            except (PermissionError, OSError):
                continue

    def has_relevant_content(self, directory_path: Path) -> bool:
        if not directory_path.is_dir():
            return False

        try:
            for entry_path in directory_path.iterdir():
                if entry_path.name.startswith("."):
                    continue

                if entry_path.is_dir():
                    return True

                if entry_path.is_file() and entry_path.suffix.lower() in [
                    *EXT_FILES_AUDIO,
                    EXT_FILE_LIBRARY,
                    EXT_FILE_RECONSTRUCTION,
                ]:
                    return True
        except (PermissionError, OSError):
            return False

        return False

    def collapse_all(self) -> None:
        self._expanded_directories.clear()

        root = self.tree.get_root()
        if not root:
            return

        for filesystem_node in list(root.children):
            if isinstance(filesystem_node, FileSystemNode):
                for child in list(filesystem_node.children):
                    child.parent = None

    def expand_directory(self, directory_node: FileSystemNode) -> None:
        if directory_node.node_type != NodeType.DIRECTORY:
            return

        directory_path = directory_node.filepath
        if not self.is_directory_expanded(directory_path):
            self._load_directory_children(directory_node)

    def is_directory_expanded(self, directory_path: Path) -> bool:
        return self._expanded_directories.get(directory_path, False)

    def collapse_directory(self, directory_path: Path) -> None:
        if directory_path in self._expanded_directories:
            del self._expanded_directories[directory_path]

    def clear_directory_children(self, directory_node: FileSystemNode) -> None:
        for child in list(directory_node.children):
            child.parent = None

    def _get_filesystems(self) -> List[Path]:
        system = System.current()

        if system == System.WINDOWS:
            return self._get_windows_drives()

        return [Path("/")]

    def _get_windows_drives(self) -> List[Path]:
        drives = []
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = Path(f"{letter}:/")
            if drive.exists():
                drives.append(drive)

        return drives

    def _get_ancestor_of_selected(self, path: Path) -> Optional[Path]:
        for selected_path in self.selected_directories:
            try:
                selected_path.relative_to(path)
                return selected_path
            except ValueError:
                continue

        return None

    def _expand_path_to_selected(
        self,
        filesystem_node: FileSystemNode,
        selected_path: Path,
    ) -> None:
        try:
            relative_parts = selected_path.relative_to(filesystem_node.filepath).parts
        except ValueError:
            return

        current_node = filesystem_node
        current_path = filesystem_node.filepath

        for part in relative_parts:
            current_path = current_path / part
            self._load_directory_children(current_node)

            for child in current_node.children:
                if isinstance(child, FileSystemNode) and child.filepath == current_path:
                    current_node = child
                    break
            else:
                break

    @property
    def selected_directories(self) -> List[Path]:
        return [
            Path.cwd(),
            self.config_manager.get_library_directory(),
            self.config_manager.get_output_directory(),
        ]
