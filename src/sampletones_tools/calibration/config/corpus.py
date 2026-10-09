from typing import Self

from pydantic import BaseModel, Field

from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.calibration.paths import CORPUS_CONFIG_PATH

from .dynamics import DynamicsConfig
from .mix import MixConfig
from .noise import NoiseConfig
from .polyphony import PolyphonyConfig
from .timbre import TimbreConfig
from .tone import ToneConfig
from .transient import TransientConfig


class CorpusConfig(BaseModel, frozen=True):
    """
    Tuning of the calibration probe corpus.

    Every probe is synthesized at unit scale and multiplied by the corpus
    amplitude, so the per-class parameters compose under one loudness
    convention. Values are loaded from the `corpus.yaml` beside this model,
    so corpus content stays reproducible across calibration runs while
    remaining adjustable in one place.
    """

    seed: int = Field(
        ge=0,
        description="Seed of the random generator behind the stochastic probes.",
    )
    item_seconds: float = Field(
        gt=0.0,
        description="Duration of every corpus item in seconds.",
    )
    amplitude: float = Field(
        gt=0.0,
        le=1.0,
        description="Scale applied to every unit-level probe.",
    )
    reference_frequency: float = Field(
        gt=0.0,
        description="Anchor tone in Hz shared by the mix, pluck, and crescendo probes.",
    )
    tone: ToneConfig = Field(
        description="Steady sine probes.",
    )
    timbre: TimbreConfig = Field(
        description="Pulse-wave probes.",
    )
    noise: NoiseConfig = Field(
        description="Broadband noise probes.",
    )
    mix: MixConfig = Field(
        description="Tone-plus-noise probes.",
    )
    transient: TransientConfig = Field(
        description="Percussive probes.",
    )
    dynamics: DynamicsConfig = Field(
        description="The level probe beside the crescendo.",
    )
    polyphony: PolyphonyConfig = Field(
        description="Probes holding more than one voice.",
    )

    @classmethod
    def load(cls) -> Self:
        """
        Load the packaged corpus tuning.

        Returns:
            The corpus configuration validated from `sampletones_tools/calibration/config/corpus.yaml`.

        Raises:
            TypeError: If the configuration file holds anything other than a mapping.
        """
        return load_yaml_model(CORPUS_CONFIG_PATH, cls)
