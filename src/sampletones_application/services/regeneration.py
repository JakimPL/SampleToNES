from __future__ import annotations

from typing import List, cast

import numpy as np

from sampletones_application.services.base import ServiceBase
from sampletones_application.services.result import ServiceCancelled, ServiceError, ServiceSuccess
from sampletones_application.utils.thread import SingleThreadExecutor
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.exporters import GENERATOR_NAME_TO_EXPORTER_MAP, Features
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.types.feature import FeatureValue

RegenerationResult = ServiceSuccess[Reconstruction] | ServiceError | ServiceCancelled


class RegenerationService(ServiceBase[RegenerationResult]):
    def __init__(self, priority: int = 0) -> None:
        super().__init__(priority)
        self._executor = SingleThreadExecutor()
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

        def task() -> None:
            self._run(reconstruction, generator_name, features, feature_key, value)

        return self._executor.execute(task, wait=False)

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

            reconstruction.update_generator_data(
                generator_name,
                instructions,
                audio,
            )
            self._emit(ServiceSuccess(value=reconstruction))
        except Exception as exception:  # pylint: disable=broad-exception-caught
            self._emit(ServiceError(exception=exception))
