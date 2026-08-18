from pathlib import Path

from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.reconstruction.browser.manager import BrowserManager
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

    def load_reconstruction(self, path: Path) -> Reconstruction:
        """Loads a reconstruction file for inspection before adding.

        Kept separate from :meth:`add_reconstruction` so the caller can inspect the
        loaded reconstruction — e.g. compare its NES frequency to the project's —
        before deciding to add it.
        """
        return Reconstruction.load(path)

    def add_reconstruction(
        self,
        reconstruction: Reconstruction,
        name: str,
    ) -> Sample:
        """Adds an already-loaded reconstruction as a sample.

        The sample embeds the reconstruction object and can be renamed afterwards
        from the samples panel.
        """
        return self._controller.add_sample(reconstruction, name=name)

    def replace_reconstruction(
        self,
        sample_id: str,
        reconstruction: Reconstruction,
    ) -> None:
        """Substitutes an existing sample's reconstruction with an already-loaded one.

        The sample keeps its identity, so the patterns referencing it sound the new
        reconstruction while their rows stay as they were.
        """
        self._controller.replace_sample_reconstruction(sample_id, reconstruction)
