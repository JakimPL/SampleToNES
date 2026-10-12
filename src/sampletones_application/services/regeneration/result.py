from dataclasses import dataclass
from typing import Mapping, Optional, Tuple, Union

import numpy as np

from sampletones_application.services.result import (
    ServiceError,
    ServiceSuccess,
)
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import Features
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.hearing import HeardRenders, Hearing


@dataclass(frozen=True)
class OriginalMix:
    """The recordings heard anywhere mixed into one waveform, beside the recordings it was mixed from.

    Attributes:
        recordings: The recordings mixed, in the document's record order.
        audio: Their mix.
    """

    recordings: Tuple[np.ndarray, ...]
    audio: np.ndarray


@dataclass(frozen=True)
class RenderedDocument:
    """A document beside its sound: every channel's render, their mix, what one hearing of it sounds, and the
    original of the recordings heard.

    The caller keeps what it asked for, so the result carries the document and the audio the
    worker rendered for it, which the landing installs where the screen reads it. A rebuild
    carries a fresh document with one channel rebuilt; a listening carries the document as it was.

    Attributes:
        reconstruction: The document the renders sound.
        channels: The audio each sounding channel of ``reconstruction`` renders to, by channel.
        mix: The whole document, summed from ``channels``.
        hearing: What the reader heard when the renders were made.
        heard: What ``hearing`` sounds of the document.
        envelopes: The envelopes each channel exports for the recordings ``hearing`` hears.
        original: The mix of the recordings ``hearing`` hears anywhere, which the waveform draws as
            the original, or ``None`` where none is heard or none loaded.
    """

    reconstruction: Reconstruction
    channels: Mapping[ChannelName, np.ndarray]
    mix: np.ndarray
    hearing: Hearing
    heard: HeardRenders
    envelopes: Mapping[ChannelName, Features]
    original: Optional[OriginalMix]


RegenerationResult = Union[
    ServiceSuccess[RenderedDocument],
    ServiceError,
]
