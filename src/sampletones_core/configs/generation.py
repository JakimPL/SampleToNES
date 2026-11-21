from typing import Self

from pydantic import ConfigDict, Field, model_validator

from sampletones_core.configs.defaults import generation_default
from sampletones_core.constants.enums import (
    AssignmentMethod,
    PhaseAlignerName,
    SelectorName,
    SpectralDistance,
)
from sampletones_core.data import DataModel


class CalculationConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)

    find_best_phase: bool = Field(default=generation_default("calculation", "find_best_phase"))
    phase_aligner: PhaseAlignerName = Field(default=generation_default("calculation", "phase_aligner"))


class WeightsConfig(DataModel):
    """How a frame's cost is composed.

    Attributes:
        spectral_loss_weight: The share of the cost the spectral term carries, before the blend is normalized.
        temporal_loss_weight: The share of the cost the temporal term carries, before the blend is normalized.
        channel_price: What each sounding channel adds to a frame's cost, on the scale of the frame's own
            sound, so a channel sounds only where it lowers the criterion by more.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)

    spectral_loss_weight: float = Field(default=generation_default("weights", "spectral_loss_weight"), ge=0.0)
    temporal_loss_weight: float = Field(default=generation_default("weights", "temporal_loss_weight"), ge=0.0)
    channel_price: float = Field(default=generation_default("weights", "channel_price"), ge=0.0)


class MetricConfig(DataModel):
    """How far a candidate stands from a target frame, bin by bin and sample by sample.

    Attributes:
        spectral_distance: The family the per-bin spectral distance belongs to.
        beta: The beta of the beta-divergence distance.
        perceptual_exponent: The power the loudness curve weighting each bin is raised to.
        temporal_level_floor: The quietest level the temporal term normalizes by, as a share of
            what one channel plays at full volume.
        silence_floor: The power a frame whose own bins lie under it is measured from, which
            holds a silent frame's cost finite.
        dynamic_range_decibels: How far under a frame's loudest bin its floor sits, which sets how
            quiet a bin stays worth covering.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=True, validate_default=True)

    spectral_distance: SpectralDistance = Field(default=generation_default("metric", "spectral_distance"))
    beta: float = Field(default=generation_default("metric", "beta"), ge=0.0)
    perceptual_exponent: float = Field(default=generation_default("metric", "perceptual_exponent"), ge=0.0)
    temporal_level_floor: float = Field(default=generation_default("metric", "temporal_level_floor"), gt=0.0)
    silence_floor: float = Field(default=generation_default("metric", "silence_floor"), gt=0.0)
    dynamic_range_decibels: float = Field(default=generation_default("metric", "dynamic_range_decibels"), gt=0.0)


class AssignmentConfig(DataModel):
    """How a frame's channels are given their candidates before the decoder reads them.

    Attributes:
        method: ``picks`` takes one channel at a time, each candidate ranked alone against what the
            earlier picks leave of the frame. ``joint`` fits every note to the frame at once and
            chooses among complete combinations of channels; it needs every channel held by one stem.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)

    method: AssignmentMethod = Field(default=generation_default("assignment", "method"))


class DecoderConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)

    selector: SelectorName = Field(default=generation_default("decoder", "selector"))
    top_k: int = Field(default=generation_default("decoder", "top_k"), ge=1)
    pitch_weight: float = Field(default=generation_default("decoder", "pitch_weight"), ge=0.0)
    volume_weight: float = Field(default=generation_default("decoder", "volume_weight"), ge=0.0)
    timbre_weight: float = Field(default=generation_default("decoder", "timbre_weight"), ge=0.0)
    on_off_weight: float = Field(default=generation_default("decoder", "on_off_weight"), ge=0.0)


class RefinementConfig(DataModel):
    """How far off the equal-tempered grid a conversion is allowed to place its notes.

    A note reaches the hardware as a divider, and the divider grid is finer than the note grid
    everywhere below the top of the range. The refinement reads where each frame's fundamental
    actually stands and bends the note it landed on toward it, so material recorded off the grid
    comes back in tune with itself.

    These settle how a bend is shaped and hold for a whole run. Which recordings bend, and on which
    channels, each stem entry states for itself.

    Attributes:
        confidence: The share of a frame's energy its harmonics must hold for its reading to count.
        change_weight: The divider steps of reading error worth avoiding one change of bend.
        window: The frames on either side whose readings a frame may settle on.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)

    confidence: float = Field(default=generation_default("refinement", "confidence"), ge=0.0, le=1.0)
    change_weight: float = Field(default=generation_default("refinement", "change_weight"), ge=0.0)
    window: int = Field(default=generation_default("refinement", "window"), ge=0)


class GenerationConfig(DataModel):
    """How a conversion chooses what every channel plays.

    The ``combinations`` decoder reads the whole combinations the ``joint`` assignment pools, so it
    runs with that assignment alone.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)

    reset_phase: bool = Field(default=generation_default("reset_phase"))

    calculation: CalculationConfig = Field(default_factory=CalculationConfig)
    weights: WeightsConfig = Field(default_factory=WeightsConfig)
    metric: MetricConfig = Field(default_factory=MetricConfig)
    assignment: AssignmentConfig = Field(default_factory=AssignmentConfig)
    decoder: DecoderConfig = Field(default_factory=DecoderConfig)
    refinement: RefinementConfig = Field(default_factory=RefinementConfig)

    @model_validator(mode="after")
    def _check_decoder_reads_the_assignment(self) -> Self:
        if self.decoder.selector == SelectorName.COMBINATIONS and self.assignment.method != AssignmentMethod.JOINT:
            raise ValueError("The combinations decoder needs the joint assignment, which pools whole combinations")

        return self
