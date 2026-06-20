from typing import FrozenSet

from pydantic import BaseModel

from sampletones_core.constants.enums import GeneratorName


class ReconstructorPanelViewModel(BaseModel, frozen=True):
    generators: FrozenSet[GeneratorName]
    drive: float
