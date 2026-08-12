from typing import FrozenSet, Optional

from pydantic import BaseModel

from sampletones_application.view_model.shared.footprint import SampleFootprintViewModel
from sampletones_core.constants.enums import GeneratorName


class ReconstructionInstrumentsViewModel(BaseModel, frozen=True):
    """What the instruments panel renders: every channel, and which of them play.

    A reconstruction holds a tab per channel whatever it sounds, so a channel standing by stays
    editable and giving it an envelope puts it in play. :attr:`playing_generators` is what the
    panel reads to mark the standing-by tabs and to offer their export.
    """

    reconstruction_loaded: bool
    playing_generators: FrozenSet[GeneratorName]
    footprint: Optional[SampleFootprintViewModel]
