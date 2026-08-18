from pathlib import Path
from typing import AbstractSet, List, Optional, Set

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_core.reconstructions.converter.paths import ConfigDirectoryFields
from sampletones_core.structures.tree import (
    FileSystemNode,
    NodeType,
    Tree,
    TreeNode,
    create_directory_node,
)
from sampletones_shared.paths.extensions import (
    EXT_FILE_LIBRARY,
    EXT_FILE_RECONSTRUCTION,
    EXT_FILES_AUDIO,
)
from sampletones_shared.utils.system.system import System


class ExplorerManager:
    """Reads the filesystem into the Main tab's tree, a folder at a time as the reader opens it.

    Two facts are held about a folder: whether its children have been read, and whether its row stands
    open. They part company — a folder the reader read and then folded away is loaded and closed — and
    the shape a session is left in is the open one, which is what a later run is handed back.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        depth: int = 0,
        *,
        language_manager: LanguageManager,
        open_directories: AbstractSet[Path],
    ) -> None:
        self._language_manager = language_manager
        self.tree = Tree()
        self.config_manager = config_manager

        self._loaded_directories: Set[Path] = set()
        self._open_directories: Set[Path] = {path for path in open_directories if path.is_dir()}
        self.depth = depth

    def refresh_tree(self) -> None:
        """Reads the filesystem afresh, down to every folder the tree has to show a row for.

        A refresh builds the tree from nothing, so ``_loaded_directories`` starts empty and each folder
        it needs is read into it once: the rows a read places under a folder stand as the walk carries
        on deeper.
        """
        self._loaded_directories.clear()
        container_root = TreeNode(
            name=self._language_manager["global.browser.label.root"],
            node_type=NodeType.ROOT,
        )

        filesystems = self._get_filesystems()
        for filesystem_path in filesystems:
            filesystem_node = self._create_directory_node(
                filesystem_path,
                parent=container_root,
            )

            for path in self._paths_to_reveal(filesystem_path):
                self._expand_path_to(filesystem_node, path)

        self.tree.set_root(container_root)

    def _paths_to_reveal(self, filesystem_path: Path) -> List[Path]:
        """The folders a refresh reads down to, among the ones this filesystem holds.

        A folder standing open is read again so it comes back open, and the directories the
        application works in are revealed so the reader finds them without walking there.
        """
        candidates = (*sorted(self._open_directories), *self.selected_directories)
        return [path for path in candidates if self._holds(filesystem_path, path)]

    def _holds(self, filesystem_path: Path, path: Path) -> bool:
        return path == filesystem_path or filesystem_path in path.parents

    def _create_directory_node(
        self,
        directory_path: Path,
        parent: Optional[TreeNode] = None,
    ) -> FileSystemNode:
        node = create_directory_node(
            directory_path,
            name=directory_path.name or str(directory_path),
            config=ConfigDirectoryFields.from_directory_name(directory_path.name),
            parent=parent,
        )

        self._load_directory_children(node)
        self._open_directories.add(node.filepath)
        return node

    def _load_directory_children(
        self,
        directory_node: FileSystemNode,
        level: int = 0,
    ) -> None:
        directory_path = directory_node.filepath
        if not directory_path.is_dir() or directory_path in self._loaded_directories:
            return

        self._loaded_directories.add(directory_path)
        try:
            entries = sorted(
                directory_path.iterdir(),
                key=lambda path: (not path.is_dir(), path.name.lower()),
            )
        except (PermissionError, OSError):
            return

        for entry_path in entries:
            try:
                if entry_path.is_dir():
                    if entry_path.name.startswith("."):
                        continue

                    child_node = create_directory_node(
                        entry_path,
                        name=entry_path.name,
                        config=ConfigDirectoryFields.from_directory_name(entry_path.name),
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
        """Folds every folder away and drops what was read, so opening one lists it as it stands."""
        self._loaded_directories.clear()
        self._open_directories.clear()

        root = self.tree.get_root()
        if not root:
            return

        for filesystem_node in list(root.children):
            if isinstance(filesystem_node, FileSystemNode):
                for child in list(filesystem_node.children):
                    child.parent = None

    def expand_directory(self, directory_node: FileSystemNode) -> None:
        """Reads a folder's children the first time it is opened, which is what fills its row."""
        if directory_node.node_type != NodeType.DIRECTORY:
            return

        self._load_directory_children(directory_node)

    def has_loaded_children(self, directory_path: Path) -> bool:
        """Whether the folder's children have been read, which is what a row below it needs."""
        return directory_path in self._loaded_directories

    def is_directory_open(self, directory_path: Path) -> bool:
        """Whether the folder's row stands open, which a refresh brings it back as."""
        return directory_path in self._open_directories

    def set_directory_open(self, directory_path: Path, is_open: bool) -> None:
        """Takes what a click left the folder standing as, which is the shape a session writes down."""
        if is_open:
            self._open_directories.add(directory_path)
            return

        self._open_directories.discard(directory_path)

    @property
    def open_directories(self) -> Set[Path]:
        """The folders standing open, which is the shape a later run is handed back."""
        return set(self._open_directories)

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

    def _expand_path_to(
        self,
        filesystem_node: FileSystemNode,
        path: Path,
    ) -> None:
        """Reads the folders down to a path, so a row stands for it and for every folder above it.

        Each folder walked through is opened, that being what shows the row below it. The folder at the
        end is read as well where it stands open, so it comes back holding what it held.
        """
        try:
            relative_parts = path.relative_to(filesystem_node.filepath).parts
        except ValueError:
            return

        current_node = filesystem_node
        current_path = filesystem_node.filepath

        for part in relative_parts:
            current_path = current_path / part
            self._load_directory_children(current_node)
            self._open_directories.add(current_node.filepath)

            child = self._child_at(current_node, current_path)
            if child is None:
                return

            current_node = child

        if self.is_directory_open(current_node.filepath):
            self._load_directory_children(current_node)

    def _child_at(
        self,
        directory_node: FileSystemNode,
        path: Path,
    ) -> Optional[FileSystemNode]:
        for child in directory_node.children:
            if isinstance(child, FileSystemNode) and child.filepath == path:
                return child

        return None

    @property
    def selected_directories(self) -> List[Path]:
        return [
            Path.cwd(),
            self.config_manager.get_library_directory(),
            self.config_manager.get_reconstructions_directory(),
        ]
