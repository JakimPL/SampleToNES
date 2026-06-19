from typing import List

from pydantic import ConfigDict, Field

from sampletones_core.constants.enums import DEFAULT_GENERATORS, GeneratorName
from sampletones_core.constants.general import (
    FAST_DIFFERENCE,
    FINAL_REGENERATION,
    FIND_BEST_PHASE,
    MAX_MIXER,
    MIXER,
    RESET_PHASE,
    SPECTRAL_LOSS_WEIGHT,
    TEMPORAL_LOSS_WEIGHT,
)
from sampletones_core.data import DataModel


class CalculationConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    find_best_phase: bool = Field(default=FIND_BEST_PHASE)
    fast_difference: bool = Field(default=FAST_DIFFERENCE)


class WeightsConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    spectral_loss_weight: float = Field(default=SPECTRAL_LOSS_WEIGHT, ge=0.0)
    temporal_loss_weight: float = Field(default=TEMPORAL_LOSS_WEIGHT, ge=0.0)


class GenerationConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mixer: float = Field(default=MIXER, ge=0.0, le=MAX_MIXER)
    reset_phase: bool = Field(default=RESET_PHASE)
    final_regeneration: bool = Field(default=FINAL_REGENERATION)

    generators: List[GeneratorName] = Field(default_factory=DEFAULT_GENERATORS.copy)
    calculation: CalculationConfig = Field(default_factory=CalculationConfig)
    weights: WeightsConfig = Field(default_factory=WeightsConfig)
