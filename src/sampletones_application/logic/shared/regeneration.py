from typing import Callable, Mapping, Protocol

import numpy as np

from sampletones_application.services.regeneration.result import RegenerationResult
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.hearing import Hearing


class ListeningServiceProtocol(Protocol):
    """The slice of the regeneration service a reader of a document's sound drives.

    A reader asks for what a hearing of a document sounds and takes the result where it lands, so
    it names the two calls that make a listening and nothing of the rebuilds. Typing the
    collaborator structurally keeps the logic layer bound to the service's result contract alone;
    the composition root supplies the real service, one instance per reader, since a result
    reaches every subscriber of the instance that made it.
    """

    def subscribe(self, handler: Callable[[RegenerationResult], None]) -> None: ...

    def start_listening(
        self,
        reconstruction: Reconstruction,
        *,
        hearing: Hearing,
        kept: Mapping[ChannelName, np.ndarray],
        recordings: Mapping[int, np.ndarray],
    ) -> None: ...
