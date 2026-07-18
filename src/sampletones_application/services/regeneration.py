from __future__ import annotations

from dataclasses import dataclass
from typing import List, cast

import numpy as np

from sampletones_application.services.base import ServiceBase
from sampletones_application.services.result import (
    ServiceCancelled,
    ServiceError,
    ServiceSuccess,
)
from sampletones_application.utils.parallelization.coalescing import LatestWinsExecutor
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.exporters import GENERATOR_NAME_TO_EXPORTER_MAP, Features
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.types.feature import FeatureValue


@dataclass(frozen=True)
class RegeneratedInstrument:
    """A regeneration result paired with the generator and feature that changed.

    Carrying the request context alongside the fresh reconstruction lets the
    history record which channel and feature an edit touched, which the finished
    reconstruction alone no longer reveals.
    """

    reconstruction: Reconstruction
    generator_name: GeneratorName
    feature_key: FeatureKey


RegenerationResult = ServiceSuccess[RegeneratedInstrument] | ServiceError | ServiceCancelled


class RegenerationService(ServiceBase[RegenerationResult]):
    """Recomputes one generator's instructions and audio for a reconstruction.

    The result is a fresh reconstruction carrying the updated generator data; the
    source reconstruction is left intact. Producing a new object lets callers swap
    the edited reconstruction in while any history snapshot that shares the prior
    object stays valid.

    Requests are serialized on a :class:`LatestWinsExecutor`: while a job runs, further
    requests coalesce to the latest one, so a continuous stream of edits collapses to a
    single applied result — the final value — instead of dropping whichever edit arrived
    mid-synthesis. ``is_running`` reports whether that worker is still busy, letting the
    view fade the reconstruction for the whole span rather than per job.
    """

    def __init__(self, priority: int = 0) -> None:
        super().__init__(priority)
        self._executor = LatestWinsExecutor()
        self._cancelled: bool = False

    def start(
        self,
        reconstruction: Reconstruction,
        generator_name: GeneratorName,
        features: Features,
        feature_key: FeatureKey,
        value: FeatureValue,
    ) -> bool:
        if self._cancelled:
            return False

        return self._executor.submit(
            lambda: self._run(
                reconstruction,
                generator_name,
                features,
                feature_key,
                value,
            )
        )

    def is_running(self) -> bool:
        return self._executor.is_running

    def cancel(self) -> None:
        self._cancelled = True

    def _run(
        self,
        reconstruction: Reconstruction,
        generator_name: GeneratorName,
        features: Features,
        feature_key: FeatureKey,
        value: FeatureValue,
    ) -> None:
        if self._cancelled:
            self._emit(ServiceCancelled())
            return
        try:
            exporter_class = GENERATOR_NAME_TO_EXPORTER_MAP[generator_name]
            generator_class = exporter_class.get_generator_type()
            features[feature_key] = value

            instructions = cast(
                List[InstructionUnion],
                exporter_class.from_features(features),
            )
            generator = generator_class(reconstruction.config, generator_name)
            audio = np.concatenate(
                [generator(instruction, save=True) for instruction in instructions],  # type: ignore[arg-type]
            )

            updated = reconstruction.model_copy(deep=True)
            updated.update_generator_data(
                generator_name,
                instructions,
                audio,
            )
            self._emit(
                ServiceSuccess(
                    value=RegeneratedInstrument(
                        reconstruction=updated,
                        generator_name=generator_name,
                        feature_key=feature_key,
                    )
                )
            )
        except Exception as exception:  # pylint: disable=broad-exception-caught
            self._emit(ServiceError(exception=exception))
