from pathlib import Path
from typing import AbstractSet, Set

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.logic.main.explorer_manager import ExplorerManager
from sampletones_core.structures.tree import FileSystemNode, Tree


class ExplorerLogic:
    def __init__(
        self,
        config_manager: ConfigManager,
        *,
        language_manager: LanguageManager,
        open_directories: AbstractSet[Path],
    ) -> None:
        self._manager = ExplorerManager(
            config_manager,
            language_manager=language_manager,
            open_directories=open_directories,
        )

    @property
    def tree(self) -> Tree:
        return self._manager.tree

    def refresh_tree(self) -> None:
        self._manager.refresh_tree()

    def has_loaded_children(self, filepath: Path) -> bool:
        return self._manager.has_loaded_children(filepath)

    def is_directory_open(self, filepath: Path) -> bool:
        return self._manager.is_directory_open(filepath)

    def set_directory_open(self, filepath: Path, is_open: bool) -> None:
        self._manager.set_directory_open(filepath, is_open)

    @property
    def open_directories(self) -> Set[Path]:
        return self._manager.open_directories

    def expand_directory(self, node: FileSystemNode) -> None:
        self._manager.expand_directory(node)

    def collapse_all(self) -> None:
        self._manager.collapse_all()

    def has_relevant_content(self, filepath: Path) -> bool:
        return self._manager.has_relevant_content(filepath)
