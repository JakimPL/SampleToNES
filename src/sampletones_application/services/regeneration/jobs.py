from dataclasses import dataclass
from typing import Mapping, Union

import numpy as np

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import Features
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.hearing import Hearing


@dataclass(frozen=True)
class RebuildJob:
    """One channel of a document rebuilt from envelopes, and the document rendered as the reader hears it.

    Attributes:
        reconstruction: The document the rebuild starts from, which stays as it is.
        channel_name: The channel rebuilt.
        features: The envelopes the channel is rebuilt from.
        hearing: What the reader hears, which names the recordings the edit writes and the reading
            rendered.
        kept: The renders the caller holds for the document's channels, by channel.
        recordings: The recordings loaded for the document, by stem id, which the original of the
            recordings heard is mixed from.
    """

    reconstruction: Reconstruction
    channel_name: ChannelName
    features: Features
    hearing: Hearing
    kept: Mapping[ChannelName, np.ndarray]
    recordings: Mapping[int, np.ndarray]


@dataclass(frozen=True)
class ListeningJob:
    """A document rendered as the reader hears it, as it stands.

    Attributes:
        reconstruction: The document read.
        hearing: What the reader hears of it.
        kept: The renders the caller holds for the document's channels, by channel.
        recordings: The recordings loaded for the document, by stem id, which the original of the
            recordings heard is mixed from.
    """

    reconstruction: Reconstruction
    hearing: Hearing
    kept: Mapping[ChannelName, np.ndarray]
    recordings: Mapping[int, np.ndarray]


RenderJob = Union[RebuildJob, ListeningJob]
