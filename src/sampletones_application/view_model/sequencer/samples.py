from typing import Tuple

from pydantic import BaseModel


class SampleEntryViewModel(BaseModel, frozen=True):
    sample_id: str
    name: str
    loop: bool


class SequencerSamplesViewModel(BaseModel, frozen=True):
    """The ordered sample pool shown in the right-hand samples panel."""

    samples: Tuple[SampleEntryViewModel, ...]
