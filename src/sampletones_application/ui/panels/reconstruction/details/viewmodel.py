from typing import FrozenSet

from pydantic import BaseModel

from sampletones_core.constants.enums import GeneratorName


class ReconstructionDetailsViewModel(BaseModel, frozen=True):
    reconstruction_loaded: bool
    available_generators: FrozenSet[GeneratorName]
    buttons_enabled: bool
