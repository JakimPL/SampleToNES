import numpy as np
from pydantic import AliasChoices, ConfigDict, Field

from sampletones_core.constants.audio import (
    DEFAULT_SAMPLE_RATE,
    MAX_SAMPLE_RATE,
    MIN_SAMPLE_RATE,
)
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.constants.general import (
    A4_FREQUENCY,
    A4_PITCH,
    DEFAULT_NES_FREQUENCY,
    LIMIT_MAX_PITCH,
    MAX_NES_FREQUENCY,
    MAX_TRANSFORMATION_GAMMA,
    MIN_FREQUENCY,
    MIN_NES_FREQUENCY,
    TRANSFORMATION_GAMMA,
)
from sampletones_core.constants.spectrum import BINS_PER_OCTAVE, CQT_CUTOFF_FREQUENCY
from sampletones_core.data import DataModel


class InstructionsLibraryConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nes_frequency: int = Field(
        default=DEFAULT_NES_FREQUENCY,
        ge=MIN_NES_FREQUENCY,
        le=MAX_NES_FREQUENCY,
        validation_alias=AliasChoices(
            "change_rate",
            "nes_frequency",
        ),
    )
    sample_rate: int = Field(
        default=DEFAULT_SAMPLE_RATE,
        ge=MIN_SAMPLE_RATE,
        le=MAX_SAMPLE_RATE,
    )
    transformation_gamma: int = Field(
        default=TRANSFORMATION_GAMMA,
        ge=MAX_TRANSFORMATION_GAMMA,
        le=MAX_TRANSFORMATION_GAMMA,
    )
    a4_frequency: float = Field(
        default=A4_FREQUENCY,
        gt=20.0,
        lt=20000.0,
    )
    a4_pitch: int = Field(
        default=A4_PITCH,
        ge=1,
        le=LIMIT_MAX_PITCH,
    )
    spectrum_method: SpectrumMethod = Field(default=SpectrumMethod.FFT)

    @property
    def frame_length(self) -> int:
        return round(self.sample_rate / self.nes_frequency)

    @property
    def window_size(self) -> int:
        if self.spectrum_method == SpectrumMethod.CQT:
            quality = 1.0 / (2.0 ** (1.0 / BINS_PER_OCTAVE) - 1.0)
            lower_bound = int(np.ceil(quality * self.sample_rate / CQT_CUTOFF_FREQUENCY))
        else:
            lower_bound = int(np.ceil(2.0 * self.sample_rate / MIN_FREQUENCY))

        return max(self.frame_length, lower_bound)
