from typing import Callable, Optional

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.view_model.sequencer.samples import (
    SampleEntryViewModel,
    SequencerSamplesViewModel,
)
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.utils.callbacks import CallbackMixin


class SequencerSamplesLogic(CallbackMixin):
    """Drives the samples panel: lists the pool and edits it via the controller.

    Adding/replacing a sample's reconstruction goes through the controller so the
    project stays the single source of truth. ``on_edit_sample_requested`` hands a
    sample id to the application, which opens that sample's reconstruction in the
    Reconstruction tab for live-linked editing.
    """

    def __init__(self, project_controller: ProjectController) -> None:
        self._controller = project_controller

        self.on_samples_changed: Optional[Callable[[SequencerSamplesViewModel], None]] = None
        self.on_edit_sample_requested: Optional[Callable[[str], None]] = None

    def build_samples(self) -> SequencerSamplesViewModel:
        entries = tuple(
            SampleEntryViewModel(
                sample_id=sample.id,
                name=sample.name,
                loop=sample.loop,
            )
            for sample in self._controller.project.samples
        )
        return SequencerSamplesViewModel(samples=entries)

    def push_samples(self) -> None:
        self.call(self.on_samples_changed, self.build_samples())

    def add_sample(self, reconstruction: Reconstruction, name: str) -> Sample:
        return self._controller.add_sample(reconstruction, name)

    def replace_sample_reconstruction(
        self,
        sample_id: str,
        reconstruction: Reconstruction,
    ) -> None:
        self._controller.replace_sample_reconstruction(sample_id, reconstruction)

    def rename_sample(self, sample_id: str, name: str) -> None:
        self._controller.rename_sample(sample_id, name)

    def remove_sample(self, sample_id: str) -> None:
        self._controller.remove_sample(sample_id)

    def set_sample_loop(self, sample_id: str, loop: bool) -> None:
        self._controller.set_sample_loop(sample_id, loop)

    def request_edit(self, sample_id: str) -> None:
        self.call(self.on_edit_sample_requested, sample_id)
