from sampletones_application.config.manager import ConfigManager
from sampletones_application.logic.reconstruction.browser_manager import BrowserManager
from sampletones_core.structures.tree import Tree
from sampletones_shared.utils.callbacks import CallbackMixin


class SequencerBrowserLogic(CallbackMixin):
    def __init__(self, config_manager: ConfigManager, browser_manager: BrowserManager) -> None:
        self._config_manager = config_manager
        self._browser_manager = browser_manager

    @property
    def tree(self) -> Tree:
        return self._browser_manager.tree

    def refresh_tree(self) -> None:
        output_directory = self._config_manager.get_output_directory()
        self._browser_manager.set_output_directory(output_directory)
