from functools import partial
from typing import Dict, List, Mapping, Optional, cast

import numpy as np

from sampletones_application.services.base import ServiceBase
from sampletones_application.services.regeneration.jobs import ListeningJob, RebuildJob, RenderJob
from sampletones_application.services.regeneration.result import (
    RegenerationResult,
    RenderedDocument,
)
from sampletones_application.services.result import ServiceError, ServiceSuccess
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_core.audio.mixing import mix
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import CHANNEL_TO_EXPORTER_MAP, Features
from sampletones_core.generators.render import render_instructions
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.renders import sounding_streams
from sampletones_core.reconstructions.reconstruction.stems.hearing import Hearing, heard_renders


class RegenerationService(ServiceBase[RegenerationResult]):
    """Recomputes one generator's instructions for a reconstruction and renders what the reader hears of it.

    An edit reaches the frames the reader hears on the channel, so the hearing travels with it:
    a frame of a recording the reader left out stands as it is, which is what lets one
    recording's part be shaped while the recordings beside it carry on.

    A rebuild's result is a fresh reconstruction carrying the updated generator data, with the
    audio of every sounding channel, their mix, what the hearing sounds of it, and the envelopes
    each channel exports for the recordings heard; the source reconstruction is left intact.
    Producing a new object lets callers swap the edited reconstruction in while any history
    snapshot that shares the prior object stays valid. A listening renders the same reading of the
    document as it stands, for a hearing the screen holds no audio for yet. Carrying the audio
    lets the landing install it where the screen reads
    it, so the render thread keeps drawing while the worker renders.

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
        *,
        hearing: Hearing,
        kept: Mapping[ChannelName, np.ndarray],
    ) -> None:
        """Rebuilds ``channel_name`` of ``reconstruction`` from ``features`` on the worker thread.

        Args:
            reconstruction: The document the rebuild starts from, which stays as it is.
            channel_name: The channel rebuilt.
            features: The envelopes the channel is rebuilt from.
            hearing: What the reader hears, which names the recordings the rebuild writes on the
                channel and the reading the result sounds.
            kept: The renders the caller holds for ``reconstruction``'s channels, by channel. Every
                channel but ``channel_name`` keeps its stream through the rebuild, so a render
                handed for it carries over into the result, and the worker renders the rest. A
                render handed for ``channel_name`` is passed over, since the edit rebuilds it.
        """
        self._execute(RebuildJob(reconstruction, channel_name, features, hearing, kept))

    def start_listening(
        self,
        reconstruction: Reconstruction,
        *,
        hearing: Hearing,
        kept: Mapping[ChannelName, np.ndarray],
    ) -> None:
        """Renders what ``hearing`` sounds of ``reconstruction`` as it stands, on the worker thread.

        Args:
            reconstruction: The document read.
            hearing: What the reader hears of it.
            kept: The renders the caller holds for ``reconstruction``'s channels, by channel, each of
                which carries over; the worker renders the rest.
        """
        self._execute(ListeningJob(reconstruction, hearing, kept))

    def _execute(self, job: RenderJob) -> None:
        self._executor.execute(partial(self._run, job), wait=True)

    def _run(self, job: RenderJob) -> None:
        try:
            match job:
                case RebuildJob():
                    document = self._rebuilt(job)
                    edited: Optional[ChannelName] = job.channel_name
                case ListeningJob():
                    document = job.reconstruction
                    edited = None

            if SingleThreadExecutor.is_shutting_down():
                return

            channels = self._rendered(document, edited, job.kept)
            mixed = mix(list(channels.values()))
            self._emit(
                ServiceSuccess(
                    value=RenderedDocument(
                        reconstruction=document,
                        channels=channels,
                        mix=mixed,
                        hearing=job.hearing,
                        heard=heard_renders(document, job.hearing, channels, mixed),
                        envelopes=document.export_heard(job.hearing.selection),
                    )
                )
            )
        except Exception as exception:  # pylint: disable=broad-exception-caught
            self._emit(ServiceError(exception=exception))

    @staticmethod
    def _rebuilt(job: RebuildJob) -> Reconstruction:
        """The document with the job's channel rebuilt from its envelopes, on the recordings the reader hears."""
        exporter_class = CHANNEL_TO_EXPORTER_MAP[job.channel_name]
        instructions = cast(
            List[InstructionUnion],
            exporter_class.from_features(job.features),
        )
        return job.reconstruction.with_channel_data(
            job.channel_name,
            instructions,
            job.features.initial_pitch,
            job.features.held_features,
            heard=job.hearing.selection.stems_for(job.channel_name),
        )

    @staticmethod
    def _rendered(
        document: Reconstruction,
        edited: Optional[ChannelName],
        kept: Mapping[ChannelName, np.ndarray],
    ) -> Dict[ChannelName, np.ndarray]:
        """The audio each sounding channel of ``document`` renders to, a handed render carried over where the
        job left the channel alone.
        """
        rendered: Dict[ChannelName, np.ndarray] = {}
        for stream in sounding_streams(document):
            handed = kept.get(stream.channel_name)
            if handed is not None and stream.channel_name != edited:
                rendered[stream.channel_name] = handed
                continue

            rendered[stream.channel_name] = render_instructions(
                [data.instruction for data in stream.instructions],
                stream.channel_name,
                document.config,
            )

        return rendered
