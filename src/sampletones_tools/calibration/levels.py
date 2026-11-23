from typing import AbstractSet, Final, Mapping, Sequence

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Window
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions import Reconstructor
from sampletones_core.reconstructions.reconstructor.level.working import WorkingLevel
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_tools.calibration.config.level import VariantLevel

TRUE_LEVEL_COEFFICIENT: Final[float] = 1.0


class TrueLevel:
    """The working level of a sound matched at the level its file holds: its recordings divided by one.

    It takes the place of the working level whole, under every level method. Paired with a
    configuration that reads files unnormalized, a sound written as NES frames reaches the matching
    at the level its frames render, which is the level its written frames fit exactly.
    """

    def coefficient(
        self,
        recordings: Sequence[np.ndarray],  # pylint: disable=unused-argument
        stems_config: StemsConfig,  # pylint: disable=unused-argument
        matcher: FrameMatcher,  # pylint: disable=unused-argument
    ) -> float:
        return TRUE_LEVEL_COEFFICIENT


def true_level(
    config: Config,  # pylint: disable=unused-argument
    channels: Mapping[ChannelName, GeneratorUnion],  # pylint: disable=unused-argument
    window: Window,  # pylint: disable=unused-argument
) -> WorkingLevel:
    """The true level, the same whatever the configuration, the channels and the window."""
    return TrueLevel()


def level_config(config: Config, level: VariantLevel) -> Config:
    """The configuration a variant converts under at ``level``: files read unnormalized at the true level."""
    match level:
        case VariantLevel.DEFAULT:
            return config
        case VariantLevel.TRUE:
            return config.model_copy(update={"general": config.general.model_copy(update={"normalize": False})})


def level_reconstructor(config: Config, channels: AbstractSet[ChannelName], level: VariantLevel) -> Reconstructor:
    """The reconstructor converting at ``level`` over ``channels``."""
    match level:
        case VariantLevel.DEFAULT:
            return Reconstructor(config, channels)
        case VariantLevel.TRUE:
            return Reconstructor(config, channels, level_factory=true_level)
