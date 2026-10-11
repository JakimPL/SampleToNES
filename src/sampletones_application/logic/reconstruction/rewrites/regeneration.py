from typing import Mapping, Protocol

import numpy as np

from sampletones_application.logic.shared.regeneration import ListeningServiceProtocol
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import Features
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.hearing import Hearing


class RegenerationServiceProtocol(ListeningServiceProtocol, Protocol):
    """The slice of the regeneration service the rewrites drive: a listening's calls, and the rebuild."""

    def start(
        self,
        reconstruction: Reconstruction,
        channel_name: ChannelName,
        features: Features,
        *,
        hearing: Hearing,
        kept: Mapping[ChannelName, np.ndarray],
    ) -> None: ...
