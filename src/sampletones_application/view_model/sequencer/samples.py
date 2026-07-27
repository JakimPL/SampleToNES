from typing import Tuple

from pydantic import BaseModel

from sampletones_core.utils.display import display_sample_label


class SampleEntryViewModel(BaseModel, frozen=True):
    sample_id: str
    name: str
    loop: bool


class SampleSelection(BaseModel, frozen=True):
    """The samples panel's selected row, offered to the sequencer as an operation target.

    Carries the sample's identity for acting on it and its position for naming it, so an
    operation reached from elsewhere in the tab — the browser's replace item — addresses the
    selection the same way the samples panel displays it.
    """

    sample_id: str
    position: int
    name: str

    @property
    def label(self) -> str:
        """The sample's list label, matching how the samples panel and tracker name it."""
        return display_sample_label(self.position, self.name)


class SequencerSamplesViewModel(BaseModel, frozen=True):
    """The ordered sample pool shown in the right-hand samples panel."""

    samples: Tuple[SampleEntryViewModel, ...]
