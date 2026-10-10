from dataclasses import dataclass
from typing import AbstractSet, Callable, List, Mapping, Tuple

import numpy as np

from sampletones_application.services.regeneration.result import (
    RegeneratedInstrument,
    RegenerationResult,
)
from sampletones_application.services.regeneration.service import RegenerationService
from sampletones_application.services.result import ServiceError, ServiceSuccess
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import Features
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.renders import rendered_channels, rendered_mix


@dataclass(frozen=True)
class HeldRebuild:
    """One rebuild the regeneration was asked for, as it was asked."""

    reconstruction: Reconstruction
    channel_name: ChannelName
    features: Features
    heard: AbstractSet[int]
    kept: Mapping[ChannelName, np.ndarray]


class HeldRegeneration:
    """The regeneration service holding each rebuild it is asked for until a case lets it finish.

    A rebuild runs on a worker thread in the application, so its result arrives some time after it
    was asked for. Holding it lets a case put gestures in between, and finishing it runs the real
    rebuild.
    """

    def __init__(self) -> None:
        self._service = RegenerationService()
        self._held: List[HeldRebuild] = []

    def subscribe(self, handler: Callable[[RegenerationResult], None]) -> None:
        self._service.subscribe(handler)

    def start(
        self,
        reconstruction: Reconstruction,
        channel_name: ChannelName,
        features: Features,
        heard: AbstractSet[int],
        *,
        kept: Mapping[ChannelName, np.ndarray],
    ) -> None:
        self._held.append(HeldRebuild(reconstruction, channel_name, features, heard, kept))

    @property
    def held(self) -> Tuple[HeldRebuild, ...]:
        """The rebuilds asked for and not yet finished, the earliest first."""
        return tuple(self._held)

    def finish(self) -> None:
        """Runs the earliest held rebuild and delivers what it produced."""
        rebuild = self._held.pop(0)
        self._service._run(
            rebuild.reconstruction,
            rebuild.channel_name,
            rebuild.features,
            rebuild.heard,
            rebuild.kept,
        )

    def finish_with(self, reconstruction: Reconstruction) -> None:
        """Delivers ``reconstruction``, rendered afresh, as what the earliest held rebuild produced."""
        self._held.pop(0)
        self._service._emit(
            ServiceSuccess(
                value=RegeneratedInstrument(
                    reconstruction=reconstruction,
                    channels=rendered_channels(reconstruction),
                    mix=rendered_mix(reconstruction),
                )
            )
        )

    def fail(self, exception: Exception) -> None:
        """Delivers ``exception`` as the earliest held rebuild's failure."""
        self._held.pop(0)
        self._service._emit(ServiceError(exception=exception))
