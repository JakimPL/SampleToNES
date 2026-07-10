from pathlib import Path
from typing import Optional

from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.logic.reconstruction.browser_manager import BrowserManager
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.structures.tree import Tree


class BrowserLogic:
    def __init__(
        self,
        config_manager: ConfigManager,
        browser_manager: BrowserManager,
    ) -> None:
        self._config_manager = config_manager
        self._browser_manager = browser_manager

    @property
    def tree(self) -> Tree:
        return self._browser_manager.tree

    def refresh_tree(self) -> None:
        reconstructions_directory = self._config_manager.get_reconstructions_directory()
        self._browser_manager.set_reconstructions_directory(reconstructions_directory)

    def resolve_original_audio(self, filepath: Path) -> Optional[Path]:
        """Reads a browsed reconstruction to recover the original audio location it records."""
        reconstruction = Reconstruction.load(filepath)
        return reconstruction.audio_filepath
