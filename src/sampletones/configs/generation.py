from types import ModuleType
from typing import List

from pydantic import ConfigDict, Field

from sampletones.constants.enums import DEFAULT_GENERATORS, GeneratorName
from sampletones.constants.general import (
    FAST_DIFFERENCE,
    FINAL_REGENERATION,
    FIND_BEST_PHASE,
    MAX_MIXER,
    MIXER,
    RESET_PHASE,
    SPECTRAL_LOSS_WEIGHT,
    TEMPORAL_LOSS_WEIGHT,
)
from sampletones.data import DataModel


class CalculationConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    find_best_phase: bool = Field(default=FIND_BEST_PHASE)
    fast_difference: bool = Field(default=FAST_DIFFERENCE)

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        from schemas.configs import FBCalculationConfig

        return FBCalculationConfig

    @classmethod
    def buffer_reader(cls) -> type:
        from schemas.configs import FBCalculationConfig

        return FBCalculationConfig.FBCalculationConfig


class WeightsConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    spectral_loss_weight: float = Field(default=SPECTRAL_LOSS_WEIGHT, ge=0.0)
    temporal_loss_weight: float = Field(default=TEMPORAL_LOSS_WEIGHT, ge=0.0)

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        from schemas.configs import FBWeightsConfig

        return FBWeightsConfig

    @classmethod
    def buffer_reader(cls) -> type:
        from schemas.configs import FBWeightsConfig

        return FBWeightsConfig.FBWeightsConfig


class GenerationConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mixer: float = Field(default=MIXER, ge=0.0, le=MAX_MIXER)
    reset_phase: bool = Field(default=RESET_PHASE)
    final_regeneration: bool = Field(default=FINAL_REGENERATION)

    generators: List[GeneratorName] = Field(default_factory=DEFAULT_GENERATORS.copy)
    calculation: CalculationConfig = Field(default_factory=CalculationConfig)
    weights: WeightsConfig = Field(default_factory=WeightsConfig)

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        from schemas.configs import FBGenerationConfig

        return FBGenerationConfig

    @classmethod
    def buffer_reader(cls) -> type:
        from schemas.configs import FBGenerationConfig

        return FBGenerationConfig.FBGenerationConfig
