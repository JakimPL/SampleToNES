from typing import Callable, Mapping, Protocol

import numpy as np

from sampletones_application.services.regeneration.result import RegenerationResult
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import Features
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.hearing import Hearing


class RegenerationServiceProtocol(Protocol):
    """The slice of the regeneration service the rewrites drive.

    Typing the collaborator structurally keeps the logic layer bound to the service's result
    contract alone; the composition root supplies the real service.
    """

    def subscribe(self, handler: Callable[[RegenerationResult], None]) -> None: ...

    def start(
        self,
        reconstruction: Reconstruction,
        channel_name: ChannelName,
        features: Features,
        *,
        hearing: Hearing,
        kept: Mapping[ChannelName, np.ndarray],
    ) -> None: ...

    def start_listening(
        self,
        reconstruction: Reconstruction,
        *,
        hearing: Hearing,
        kept: Mapping[ChannelName, np.ndarray],
    ) -> None: ...
