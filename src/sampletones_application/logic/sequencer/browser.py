from pathlib import Path

from sampletones_application.logic.project.controller import ProjectController
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.utils.callbacks import CallbackMixin


class SequencerBrowserLogic(CallbackMixin):
    """What the sequencer does with a reconstruction its browser offers: reads it and takes it into
    the song as a sample, beside the browsing every reconstruction browser shares."""

    def __init__(self, project_controller: ProjectController) -> None:
        self._controller = project_controller

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

        The sample embeds the reconstruction object and can be renamed afterward
        from the samples panel.
        """
        return self._controller.add_sample(reconstruction, name=name)

    def replace_reconstruction(
        self,
        voice_id: str,
        reconstruction: Reconstruction,
    ) -> Reconstruction:
        """Substitutes an existing sample's reconstruction with an already-loaded one.

        The sample keeps its identity, so the patterns referencing it sound the new
        reconstruction while their rows stay as they were.

        Returns:
            Reconstruction: The document the sample now holds, in the form the project keeps it.
        """
        return self._controller.replace_sample_reconstruction(voice_id, reconstruction)
