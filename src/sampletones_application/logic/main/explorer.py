from pathlib import Path

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.manager import ConfigManager
from sampletones_application.logic.main.explorer_manager import ExplorerManager
from sampletones_core.structures.tree import FileSystemNode, Tree


class ExplorerLogic:
    def __init__(
        self,
        config_manager: ConfigManager,
        *,
        language_manager: LanguageManager,
    ) -> None:
        self._manager = ExplorerManager(
            config_manager,
            language_manager=language_manager,
        )

    @property
    def tree(self) -> Tree:
        return self._manager.tree

    def refresh_tree(self) -> None:
        self._manager.refresh_tree()

    def is_directory_expanded(self, filepath: Path) -> bool:
        return self._manager.is_directory_expanded(filepath)

    def expand_directory(self, node: FileSystemNode) -> None:
        self._manager.expand_directory(node)

    def collapse_all(self) -> None:
        self._manager.collapse_all()

    def has_relevant_content(self, filepath: Path) -> bool:
        return self._manager.has_relevant_content(filepath)
