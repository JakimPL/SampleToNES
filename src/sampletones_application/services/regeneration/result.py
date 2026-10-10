from dataclasses import dataclass
from typing import Mapping, Union

import numpy as np

from sampletones_application.services.result import (
    ServiceError,
    ServiceSuccess,
)
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction


@dataclass(frozen=True)
class RegeneratedInstrument:
    """A reconstruction with one channel rebuilt from the envelopes the regeneration was handed, and its sound.

    The caller keeps what it asked for, so the result carries the rebuilt document and the audio
    the worker rendered for it, which the landing installs where the screen reads it.

    Attributes:
        reconstruction: The fresh reconstruction carrying the rebuilt channel.
        channels: The audio each sounding channel of ``reconstruction`` renders to, by channel.
        mix: The whole reconstruction, summed from ``channels``.
    """

    reconstruction: Reconstruction
    channels: Mapping[ChannelName, np.ndarray]
    mix: np.ndarray


RegenerationResult = Union[
    ServiceSuccess[RegeneratedInstrument],
    ServiceError,
]
