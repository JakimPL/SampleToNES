from enum import StrEnum
from typing import Tuple

from pydantic import BaseModel

from sampletones_core.utils.display import display_voice_label


class VoiceKind(StrEnum):
    """Which of the two kinds a voice list entry carries.

    A sample stands on a recording it was converted from; an instrument was written by hand. The list
    marks each so a reader tells them apart, and the gestures a row offers follow from it.
    """

    SAMPLE = "sample"
    INSTRUMENT = "instrument"


class VoiceEntryViewModel(BaseModel, frozen=True):
    voice_id: str
    name: str
    kind: VoiceKind
    loop: bool


class VoiceSelection(BaseModel, frozen=True):
    """The voices panel's selected row, offered to the sequencer as an operation target.

    Carries the voice's identity for acting on it and its position for naming it, so an
    operation reached from elsewhere in the tab — the browser's replace item — addresses the
    selection the same way the voices panel displays it.
    """

    voice_id: str
    position: int
    name: str
    kind: VoiceKind

    @property
    def label(self) -> str:
        """The voice's list label, matching how the voices panel and tracker name it."""
        return display_voice_label(self.position, self.name)


class SequencerVoicesViewModel(BaseModel, frozen=True):
    """The ordered voice pool shown in the right-hand voices panel."""

    voices: Tuple[VoiceEntryViewModel, ...]
