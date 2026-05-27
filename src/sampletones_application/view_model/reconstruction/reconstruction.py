from typing import FrozenSet

from pydantic import BaseModel

from sampletones_core.constants.enums import GeneratorName


class ReconstructionViewModel(BaseModel, frozen=True):
    reconstruction_loaded: bool
    available_generators: FrozenSet[GeneratorName]
    audio_source_enabled: bool
    buttons_enabled: bool
