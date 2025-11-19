from types import ModuleType

import numpy as np
from pydantic import ConfigDict, Field

from sampletones.constants.general import (
    A4_FREQUENCY,
    A4_PITCH,
    DEFAULT_CHANGE_RATE,
    DEFAULT_SAMPLE_RATE,
    MAX_CHANGE_RATE,
    MAX_SAMPLE_RATE,
    MAX_TRANSFORMATION_GAMMA,
    MIN_CHANGE_RATE,
    MIN_FREQUENCY,
    MIN_SAMPLE_RATE,
    TRANSFORMATION_GAMMA,
)
from sampletones.data import DataModel


class LibraryConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    change_rate: int = Field(default=DEFAULT_CHANGE_RATE, ge=MIN_CHANGE_RATE, le=MAX_CHANGE_RATE)
    sample_rate: int = Field(default=DEFAULT_SAMPLE_RATE, ge=MIN_SAMPLE_RATE, le=MAX_SAMPLE_RATE)
    transformation_gamma: int = Field(default=TRANSFORMATION_GAMMA, ge=0, le=MAX_TRANSFORMATION_GAMMA)
    a4_frequency: float = Field(default=A4_FREQUENCY, gt=20.0, lt=20000.0)
    a4_pitch: int = Field(default=A4_PITCH, ge=1, le=127)

    @property
    def frame_length(self) -> int:
        return round(self.sample_rate / self.change_rate)

    @property
    def window_size(self) -> int:
        lower_bound = int(np.ceil(2.0 * self.sample_rate / MIN_FREQUENCY))
        return max(self.frame_length, lower_bound)

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        from schemas.configs import FBLibraryConfig

        return FBLibraryConfig

    @classmethod
    def buffer_reader(cls) -> type:
        from schemas.configs import FBLibraryConfig

        return FBLibraryConfig.FBLibraryConfig
