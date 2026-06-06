from typing import Callable, Optional

from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.logic.reconstruction.browser_manager import BrowserManager
from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_core.structures.tree import Tree
from sampletones_shared.types.callback import PathCallback, VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin

OnReconstructionLoadedCallback = Callable[[ReconstructionData], None]


class BrowserLogic(CallbackMixin):
    def __init__(
        self,
        config_manager: ConfigManager,
        browser_manager: BrowserManager,
    ) -> None:
        self._config_manager = config_manager
        self._browser_manager = browser_manager

        self.load_reconstruction_with_confirmation: Optional[PathCallback] = None
        self.on_reconstruction_loaded: Optional[OnReconstructionLoadedCallback] = None
        self.on_reconstruct_file: Optional[VoidCallback] = None
        self.on_reconstruct_directory: Optional[VoidCallback] = None

    @property
    def tree(self) -> Tree:
        return self._browser_manager.tree

    def refresh_tree(self) -> None:
        reconstructions_directory = self._config_manager.get_reconstructions_directory()
        self._browser_manager.set_reconstructions_directory(reconstructions_directory)
