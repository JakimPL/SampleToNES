from functools import partial
from typing import AbstractSet, List, cast

from sampletones_application.services.base import ServiceBase
from sampletones_application.services.regeneration.result import (
    RegeneratedInstrument,
    RegenerationResult,
)
from sampletones_application.services.result import ServiceError, ServiceSuccess
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import CHANNEL_TO_EXPORTER_MAP, Features
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions import Reconstruction


class RegenerationService(ServiceBase[RegenerationResult]):
    """Recomputes one generator's instructions for a reconstruction.

    An edit reaches the frames the reader hears on the channel, so ``heard`` travels with it:
    a frame of a recording the reader left out stands as it is, which is what lets one
    recording's part be shaped while the recordings beside it carry on.

    The result is a fresh reconstruction carrying the updated generator data; the
    source reconstruction is left intact. Producing a new object lets callers swap
    the edited reconstruction in while any history snapshot that shares the prior
    object stays valid.

    One job runs at a time on a single worker thread. Its caller starts the next job once the
    previous result has arrived, so each rebuild starts from the document the one before it left.
    """

    def __init__(self, priority: int = 0) -> None:
        super().__init__(priority)
        self._executor = SingleThreadExecutor()

    def start(
        self,
        reconstruction: Reconstruction,
        channel_name: ChannelName,
        features: Features,
        heard: AbstractSet[int],
    ) -> None:
        """Rebuilds ``channel_name`` of ``reconstruction`` from ``features`` on the worker thread.

        Args:
            reconstruction: The document the rebuild starts from, which stays as it is.
            channel_name: The channel rebuilt.
            features: The envelopes the channel is rebuilt from.
            heard: The recordings whose frames the rebuild writes.
        """
        self._executor.execute(
            partial(
                self._run,
                reconstruction,
                channel_name,
                features,
                heard,
            ),
            wait=True,
        )

    def _run(
        self,
        reconstruction: Reconstruction,
        channel_name: ChannelName,
        features: Features,
        heard: AbstractSet[int],
    ) -> None:
        try:
            exporter_class = CHANNEL_TO_EXPORTER_MAP[channel_name]
            instructions = cast(
                List[InstructionUnion],
                exporter_class.from_features(features),
            )

            updated = reconstruction.with_channel_data(
                channel_name,
                instructions,
                features.initial_pitch,
                features.held_features,
                heard=heard,
            )
            self._emit(ServiceSuccess(value=RegeneratedInstrument(reconstruction=updated)))
        except Exception as exception:  # pylint: disable=broad-exception-caught
            self._emit(ServiceError(exception=exception))
