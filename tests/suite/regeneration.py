from typing import Callable, List, Mapping, Tuple

import numpy as np

from sampletones_application.services.regeneration.jobs import ListeningJob, RebuildJob, RenderJob
from sampletones_application.services.regeneration.result import (
    RegenerationResult,
    RenderedDocument,
)
from sampletones_application.services.regeneration.service import RegenerationService
from sampletones_application.services.result import ServiceError, ServiceSuccess
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import Features
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.renders import rendered_channels, rendered_mix
from sampletones_core.reconstructions.reconstruction.stems.hearing import Hearing, heard_renders


class HeldRegeneration:
    """The regeneration service holding each job it is asked for until a case lets it finish.

    A job runs on a worker thread in the application, so its result arrives some time after it
    was asked for. Holding it lets a case put gestures in between, and finishing it runs the real
    job.
    """

    def __init__(self) -> None:
        self._service = RegenerationService()
        self._held: List[RenderJob] = []

    def subscribe(self, handler: Callable[[RegenerationResult], None]) -> None:
        self._service.subscribe(handler)

    def start(
        self,
        reconstruction: Reconstruction,
        channel_name: ChannelName,
        features: Features,
        *,
        hearing: Hearing,
        kept: Mapping[ChannelName, np.ndarray],
    ) -> None:
        self._held.append(RebuildJob(reconstruction, channel_name, features, hearing, kept))

    def start_listening(
        self,
        reconstruction: Reconstruction,
        *,
        hearing: Hearing,
        kept: Mapping[ChannelName, np.ndarray],
    ) -> None:
        self._held.append(ListeningJob(reconstruction, hearing, kept))

    @property
    def held(self) -> Tuple[RenderJob, ...]:
        """The jobs asked for and not yet finished, the earliest first."""
        return tuple(self._held)

    def finish(self) -> None:
        """Runs the earliest held job and delivers what it produced."""
        self._service._run(self._held.pop(0))

    def finish_with(self, reconstruction: Reconstruction) -> None:
        """Delivers ``reconstruction``, rendered afresh for the hearing the earliest held job was asked with, as
        what that job produced.
        """
        job = self._held.pop(0)
        channels = rendered_channels(reconstruction)
        mixed = rendered_mix(reconstruction)
        self._service._emit(
            ServiceSuccess(
                value=RenderedDocument(
                    reconstruction=reconstruction,
                    channels=channels,
                    mix=mixed,
                    hearing=job.hearing,
                    heard=heard_renders(reconstruction, job.hearing, channels, mixed),
                    envelopes=reconstruction.export_heard(job.hearing.selection),
                )
            )
        )

    def fail(self, exception: Exception) -> None:
        """Delivers ``exception`` as the earliest held job's failure."""
        self._held.pop(0)
        self._service._emit(ServiceError(exception=exception))
