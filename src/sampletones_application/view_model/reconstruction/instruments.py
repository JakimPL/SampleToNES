from typing import FrozenSet, Optional

from pydantic import BaseModel

from sampletones_application.view_model.shared.footprint import SampleFootprintViewModel
from sampletones_core.constants.enums import GeneratorName


class ReconstructionInstrumentsViewModel(BaseModel, frozen=True):
    reconstruction_loaded: bool
    available_generators: FrozenSet[GeneratorName]
    footprint: Optional[SampleFootprintViewModel]
