from dataclasses import dataclass
from typing import Mapping, Union

import numpy as np

from sampletones_application.services.result import (
    ServiceError,
    ServiceSuccess,
)
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.hearing import HeardRenders, Hearing


@dataclass(frozen=True)
class RenderedDocument:
    """A document beside its sound: every channel's render, their mix, and what one hearing of it sounds.

    The caller keeps what it asked for, so the result carries the document and the audio the
    worker rendered for it, which the landing installs where the screen reads it. A rebuild
    carries a fresh document with one channel rebuilt; a listening carries the document as it was.

    Attributes:
        reconstruction: The document the renders sound.
        channels: The audio each sounding channel of ``reconstruction`` renders to, by channel.
        mix: The whole document, summed from ``channels``.
        hearing: What the reader heard when the renders were made.
        heard: What ``hearing`` sounds of the document.
    """

    reconstruction: Reconstruction
    channels: Mapping[ChannelName, np.ndarray]
    mix: np.ndarray
    hearing: Hearing
    heard: HeardRenders


RegenerationResult = Union[
    ServiceSuccess[RenderedDocument],
    ServiceError,
]
