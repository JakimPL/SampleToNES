from typing import Final, Self, assert_never

from pydantic import ConfigDict, Field, model_validator

from sampletones_core.configs.defaults import generation_default
from sampletones_core.constants.enums import (
    AssignmentMethod,
    ChannelName,
    PhaseAlignerName,
    SelectorName,
    SpectralDistance,
)
from sampletones_core.data import DataModel

PASSES_HEARD_ALONE: Final[int] = 1


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


class ChannelInertia(DataModel):
    """How strongly each channel keeps to what the frames beside a frame play in the neighbor pass.

    A frame's choice pays this many times the decoder's charges for a channel changing from the frame
    before and to the frame after. The columns and pools the decoder reads carry the same charge, on
    top of which the decoder charges its own changes between frames. The analysis window averages a
    channel over several frames, so a channel switched on and off from frame to frame reads as a
    level between the two, which the ear hears as flicker. A channel at ``0`` chooses freely of its
    neighbors, as short drum hits need. Each channel belongs to one stem, so a stem's channels take
    their own values.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)

    pulse1: float = Field(default=generation_default("assignment", "inertia", "pulse1"), ge=0.0)
    pulse2: float = Field(default=generation_default("assignment", "inertia", "pulse2"), ge=0.0)
    triangle: float = Field(default=generation_default("assignment", "inertia", "triangle"), ge=0.0)
    noise: float = Field(default=generation_default("assignment", "inertia", "noise"), ge=0.0)

    @property
    def binding(self) -> bool:
        """Whether any channel keeps to its neighbors."""
        return any(inertia > 0 for inertia in (self.pulse1, self.pulse2, self.triangle, self.noise))

    def of(self, channel_name: ChannelName) -> float:
        """The inertia of ``channel_name``."""
        match channel_name:
            case ChannelName.PULSE1:
                return self.pulse1
            case ChannelName.PULSE2:
                return self.pulse2
            case ChannelName.TRIANGLE:
                return self.triangle
            case ChannelName.NOISE:
                return self.noise
            case _:
                assert_never(channel_name)


class AssignmentConfig(DataModel):
    """How a frame's channels are given their candidates before the decoder reads them.

    Attributes:
        method: ``picks`` takes one channel at a time, each candidate ranked alone against what the
            earlier picks leave of the frame. ``joint`` fits every note to the frame at once and
            chooses among complete combinations of channels; it needs every channel held by one stem.
        neighbors: How many times every frame is assigned again after a decode, among the notes
            its neighbors were decoded to play, each time decoded anew. The ``joint`` assignment
            alone hears its neighbors.
        inertia: How strongly each channel of a frame assigned again keeps to what the frames
            beside it play.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)

    method: AssignmentMethod = Field(default=generation_default("assignment", "method"))
    neighbors: int = Field(default=generation_default("assignment", "neighbors"), ge=0)
    inertia: ChannelInertia = Field(default_factory=ChannelInertia)

    @property
    def passes(self) -> int:
        """How many times a run assigns every frame: once heard alone, then once in each neighbor pass."""
        return PASSES_HEARD_ALONE + self.neighbors


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

    The ``combinations`` decoder reads the whole combinations the ``joint`` assignment pools, and a
    frame is heard among its neighbors by that assignment, so both run with it alone. Inertia keeps
    a frame's choice to its neighbors in that pass, so it runs with the pass.
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

    @model_validator(mode="after")
    def _check_neighbors_are_heard(self) -> Self:
        if self.assignment.neighbors > 0 and self.assignment.method != AssignmentMethod.JOINT:
            raise ValueError("Assigning frames among their neighbors needs the joint assignment")

        return self

    @model_validator(mode="after")
    def _check_inertia_has_neighbors(self) -> Self:
        if self.assignment.inertia.binding and self.assignment.neighbors == 0:
            raise ValueError("Keeping a frame's choice to its neighbors needs the neighbor pass")

        return self
