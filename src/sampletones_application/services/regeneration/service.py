from typing import List, cast

from sampletones_application.services.base import ServiceBase
from sampletones_application.services.regeneration.result import (
    RegeneratedInstrument,
    RegenerationResult,
)
from sampletones_application.services.result import (
    ServiceCanceled,
    ServiceError,
    ServiceSuccess,
)
from sampletones_application.utils.parallelization.coalescing import LatestWinsExecutor
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import CHANNEL_TO_EXPORTER_MAP, Features
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions import Reconstruction


class RegenerationService(ServiceBase[RegenerationResult]):
    """Recomputes one generator's instructions for a reconstruction.

    The result is a fresh reconstruction carrying the updated generator data; the
    source reconstruction is left intact. Producing a new object lets callers swap
    the edited reconstruction in while any history snapshot that shares the prior
    object stays valid.

    Requests are serialized on a :class:`LatestWinsExecutor`: while a job runs, further
    requests coalesce to the latest one, so a continuous stream of edits collapses to a
    single applied result — the final value. ``is_running`` reports whether that worker is
    still busy, letting the view fade the reconstruction for the whole busy span.
    """

    def __init__(self, priority: int = 0) -> None:
        super().__init__(priority)
        self._executor = LatestWinsExecutor()
        self._canceled: bool = False

    def start(
        self,
        reconstruction: Reconstruction,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        features: Features,
    ) -> bool:
        if self._canceled:
            return False

        return self._executor.submit(
            lambda: self._run(
                reconstruction,
                channel_name,
                feature_key,
                features,
            )
        )

    def is_running(self) -> bool:
        return self._executor.is_running

    def cancel(self) -> None:
        self._canceled = True

    def _run(
        self,
        reconstruction: Reconstruction,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        features: Features,
    ) -> None:
        if self._canceled:
            self._emit(ServiceCanceled())
            return
        try:
            exporter_class = CHANNEL_TO_EXPORTER_MAP[channel_name]
            instructions = cast(
                List[InstructionUnion],
                exporter_class.from_features(features),
            )

            updated = reconstruction.model_copy(deep=True)
            updated.update_channel_data(
                channel_name,
                instructions,
                features.initial_pitch,
                features.held_features,
            )
            self._emit(
                ServiceSuccess(
                    value=RegeneratedInstrument(
                        reconstruction=updated,
                        channel_name=channel_name,
                        feature_key=feature_key,
                    )
                )
            )
        except Exception as exception:  # pylint: disable=broad-exception-caught
            self._emit(ServiceError(exception=exception))
