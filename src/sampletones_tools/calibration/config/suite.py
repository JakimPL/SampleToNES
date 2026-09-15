from typing import Annotated, Self, Tuple

from pydantic import BaseModel, Field, NonNegativeFloat

from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.calibration.paths import SUITE_CONFIG_PATH

TemporalWeight = Annotated[float, Field(ge=0.0, le=1.0)]


class SuiteConfig(BaseModel, frozen=True):
    """
    The sweep a calibration run measures when the command line names none of its parts.

    Values are loaded from the packaged `suite.yaml` beside the corpus and the referee tuning, so
    a run with no options measures the same configurations on every machine. An option on the
    command line replaces the part of the suite it names.
    """

    methods: Tuple[SpectrumMethod, ...] = Field(
        min_length=1,
        description="Spectrum methods measured, one variant each.",
    )
    perceptual_exponents: Tuple[NonNegativeFloat, ...] = Field(
        min_length=1,
        description="Values of metric.perceptual_exponent measured.",
    )
    temporal_weights: Tuple[TemporalWeight, ...] = Field(
        description="Values of weights.temporal_loss_weight measured; empty keeps the base blend.",
    )
    channels: Tuple[ChannelName, ...] = Field(
        min_length=1,
        description="Channels every variant reconstructs with.",
    )

    @classmethod
    def load(cls) -> Self:
        """
        Load the packaged suite.

        Returns:
            The suite validated from `sampletones_tools/calibration/config/suite.yaml`.

        Raises:
            TypeError: If the configuration file holds anything other than a mapping.
        """
        return load_yaml_model(SUITE_CONFIG_PATH, cls)
