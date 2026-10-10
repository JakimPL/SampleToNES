from functools import partial
from typing import AbstractSet, Dict, List, Mapping, cast

import numpy as np

from sampletones_application.services.base import ServiceBase
from sampletones_application.services.regeneration.result import (
    RegeneratedInstrument,
    RegenerationResult,
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


class RegenerationService(ServiceBase[RegenerationResult]):
    """Recomputes one generator's instructions for a reconstruction and renders what the document then sounds.

    An edit reaches the frames the reader hears on the channel, so ``heard`` travels with it:
    a frame of a recording the reader left out stands as it is, which is what lets one
    recording's part be shaped while the recordings beside it carry on.

    The result is a fresh reconstruction carrying the updated generator data, with the audio of
    every sounding channel and their mix; the source reconstruction is left intact. Producing a
    new object lets callers swap the edited reconstruction in while any history snapshot that
    shares the prior object stays valid. Carrying the audio lets the landing install it where the
    screen reads it, so the render thread keeps drawing while the worker renders.

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
        *,
        kept: Mapping[ChannelName, np.ndarray],
    ) -> None:
        """Rebuilds ``channel_name`` of ``reconstruction`` from ``features`` on the worker thread.

        Args:
            reconstruction: The document the rebuild starts from, which stays as it is.
            channel_name: The channel rebuilt.
            features: The envelopes the channel is rebuilt from.
            heard: The recordings whose frames the rebuild writes.
            kept: The renders the caller holds for ``reconstruction``'s channels, by channel. Every
                channel but ``channel_name`` keeps its stream through the rebuild, so a render
                handed for it carries over into the result, and the worker renders the rest. A
                render handed for ``channel_name`` is passed over, since the edit rebuilds it.
        """
        self._executor.execute(
            partial(
                self._run,
                reconstruction,
                channel_name,
                features,
                heard,
                kept,
            ),
            wait=True,
        )

    def _run(
        self,
        reconstruction: Reconstruction,
        channel_name: ChannelName,
        features: Features,
        heard: AbstractSet[int],
        kept: Mapping[ChannelName, np.ndarray],
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
            if SingleThreadExecutor.is_shutting_down():
                return

            channels = self._rendered(updated, channel_name, kept)
            self._emit(
                ServiceSuccess(
                    value=RegeneratedInstrument(
                        reconstruction=updated,
                        channels=channels,
                        mix=mix(list(channels.values())),
                    )
                )
            )
        except Exception as exception:  # pylint: disable=broad-exception-caught
            self._emit(ServiceError(exception=exception))

    @staticmethod
    def _rendered(
        updated: Reconstruction,
        edited: ChannelName,
        kept: Mapping[ChannelName, np.ndarray],
    ) -> Dict[ChannelName, np.ndarray]:
        """The audio each sounding channel of ``updated`` renders to, a handed render carried over where the
        edit left the channel alone.
        """
        rendered: Dict[ChannelName, np.ndarray] = {}
        for stream in sounding_streams(updated):
            handed = kept.get(stream.channel_name)
            if handed is not None and stream.channel_name != edited:
                rendered[stream.channel_name] = handed
                continue

            rendered[stream.channel_name] = render_instructions(
                [data.instruction for data in stream.instructions],
                stream.channel_name,
                updated.config,
            )

        return rendered
