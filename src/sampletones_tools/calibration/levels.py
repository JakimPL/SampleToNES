from typing import AbstractSet, Final

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstructor
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_tools.calibration.config.level import WorkingLevel

TRUE_LEVEL_COEFFICIENT: Final[float] = 1.0


class TrueLevelReconstructor(Reconstructor):
    """A reconstructor matching every sound at the level its file holds, its working level one.

    Paired with a configuration that reads files unnormalized, a sound written as NES frames reaches
    the matching at the level its frames render, which is the level its written frames fit exactly.
    """

    def get_coefficient(self, audio: np.ndarray, stems_config: StemsConfig) -> float:
        return TRUE_LEVEL_COEFFICIENT


def level_config(config: Config, level: WorkingLevel) -> Config:
    """The configuration a variant converts under at ``level``: files read unnormalized at the true level."""
    match level:
        case WorkingLevel.DEFAULT:
            return config
        case WorkingLevel.TRUE:
            return config.model_copy(update={"general": config.general.model_copy(update={"normalize": False})})


def level_reconstructor(config: Config, channels: AbstractSet[ChannelName], level: WorkingLevel) -> Reconstructor:
    """The reconstructor converting at ``level`` over ``channels``."""
    match level:
        case WorkingLevel.DEFAULT:
            return Reconstructor(config, channels)
        case WorkingLevel.TRUE:
            return TrueLevelReconstructor(config, channels)
