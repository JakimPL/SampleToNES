from typing import List

from pydantic import AliasChoices, ConfigDict, Field

from sampletones_core.constants.algorithm import (
    DECODER_TOP_K,
    DIVERGENCE_BETA,
    DRIVE,
    FAST_DIFFERENCE,
    FINAL_REGENERATION,
    FIND_BEST_PHASE,
    MAX_DRIVE,
    PERCEPTUAL_EXPONENT,
    PHASE_ALIGNER,
    RESET_PHASE,
    SELECTOR,
    SPECTRAL_DISTANCE,
    SPECTRAL_LOSS_WEIGHT,
    TEMPORAL_LEVEL_FLOOR,
    TEMPORAL_LOSS_WEIGHT,
    TRANSITION_ON_OFF_WEIGHT,
    TRANSITION_PITCH_WEIGHT,
    TRANSITION_TIMBRE_WEIGHT,
    TRANSITION_VOLUME_WEIGHT,
)
from sampletones_core.constants.enums import (
    DEFAULT_GENERATORS,
    GeneratorName,
    PhaseAlignerName,
    SelectorName,
    SpectralDistance,
)
from sampletones_core.data import DataModel


class CalculationConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    find_best_phase: bool = Field(default=FIND_BEST_PHASE)
    fast_difference: bool = Field(default=FAST_DIFFERENCE)
    phase_aligner: PhaseAlignerName = Field(default=PHASE_ALIGNER)


class WeightsConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    spectral_loss_weight: float = Field(default=SPECTRAL_LOSS_WEIGHT, ge=0.0)
    temporal_loss_weight: float = Field(default=TEMPORAL_LOSS_WEIGHT, ge=0.0)


class MetricConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=True)

    spectral_distance: SpectralDistance = Field(default=SPECTRAL_DISTANCE)
    beta: float = Field(default=DIVERGENCE_BETA, ge=0.0)
    perceptual_exponent: float = Field(default=PERCEPTUAL_EXPONENT, ge=0.0)
    temporal_level_floor: float = Field(default=TEMPORAL_LEVEL_FLOOR, gt=0.0)


class DecoderConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    selector: SelectorName = Field(default=SELECTOR)
    top_k: int = Field(default=DECODER_TOP_K, ge=1)
    pitch_weight: float = Field(default=TRANSITION_PITCH_WEIGHT, ge=0.0)
    volume_weight: float = Field(default=TRANSITION_VOLUME_WEIGHT, ge=0.0)
    timbre_weight: float = Field(default=TRANSITION_TIMBRE_WEIGHT, ge=0.0)
    on_off_weight: float = Field(default=TRANSITION_ON_OFF_WEIGHT, ge=0.0)


class GenerationConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    drive: float = Field(
        default=DRIVE,
        gt=0.0,
        le=MAX_DRIVE,
        validation_alias=AliasChoices(
            "drive",
            "mixer",
        ),
    )

    reset_phase: bool = Field(default=RESET_PHASE)
    final_regeneration: bool = Field(default=FINAL_REGENERATION)

    generators: List[GeneratorName] = Field(default_factory=DEFAULT_GENERATORS.copy)
    calculation: CalculationConfig = Field(default_factory=CalculationConfig)
    weights: WeightsConfig = Field(default_factory=WeightsConfig)
    metric: MetricConfig = Field(default_factory=MetricConfig)
    decoder: DecoderConfig = Field(default_factory=DecoderConfig)
