from pathlib import Path

from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.reconstruction.browser_manager import BrowserManager
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.structures.tree import Tree
from sampletones_shared.utils.callbacks import CallbackMixin


class SequencerBrowserLogic(CallbackMixin):
    def __init__(
        self,
        config_manager: ConfigManager,
        browser_manager: BrowserManager,
        project_controller: ProjectController,
    ) -> None:
        self._config_manager = config_manager
        self._browser_manager = browser_manager
        self._controller = project_controller

    @property
    def tree(self) -> Tree:
        return self._browser_manager.tree

    def refresh_tree(self) -> None:
        reconstructions_directory = self._config_manager.get_reconstructions_directory()
        self._browser_manager.set_reconstructions_directory(reconstructions_directory)

    def import_reconstruction(self, path: Path) -> Sample:
        """Loads a reconstruction file from the browser and adds it as a sample.

        The sample embeds the loaded reconstruction object; its name defaults to
        the file stem and can be renamed afterwards from the samples panel.
        """
        reconstruction = Reconstruction.load(path)
        return self._controller.add_sample(reconstruction, name=path.stem)
