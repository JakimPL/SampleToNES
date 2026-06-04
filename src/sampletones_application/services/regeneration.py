from __future__ import annotations

from typing import List, cast

import numpy as np

from sampletones_application.services.base import ServiceBase
from sampletones_application.services.result import ServiceError, ServiceSuccess
from sampletones_application.utils.thread import SingleThreadExecutor
from sampletones_application.view_model.reconstruction.data import ReconstructionData
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.exporters import GENERATOR_NAME_TO_EXPORTER_MAP, Features
from sampletones_core.instructions import InstructionUnion
from sampletones_core.types.feature import FeatureValue

RegenerationResult = ServiceSuccess[ReconstructionData] | ServiceError


class RegenerationService(ServiceBase[RegenerationResult]):
    def __init__(self, priority: int = 0) -> None:
        super().__init__(priority)
        self._executor = SingleThreadExecutor()

    def start(
        self,
        reconstruction_data: ReconstructionData,
        generator_name: GeneratorName,
        features: Features,
        feature_key: FeatureKey,
        data: FeatureValue,
    ) -> bool:
        def task() -> None:
            self._run(reconstruction_data, generator_name, features, feature_key, data)

        return self._executor.execute(task, wait=False)

    def _run(
        self,
        reconstruction_data: ReconstructionData,
        generator_name: GeneratorName,
        features: Features,
        feature_key: FeatureKey,
        data: FeatureValue,
    ) -> None:
        try:
            config = reconstruction_data.config
            exporter_class = GENERATOR_NAME_TO_EXPORTER_MAP[generator_name]
            generator_class = exporter_class.get_generator_type()
            features[feature_key] = data

            instructions = cast(
                List[InstructionUnion],
                exporter_class.from_features(features),
            )
            generator = generator_class(config, generator_name)
            audio = np.concatenate(
                [generator(instruction, save=True) for instruction in instructions],  # type: ignore[arg-type]
            )

            reconstruction_data.reconstruction.update_generator_data(
                generator_name,
                instructions,
                audio,
            )
            self._emit(ServiceSuccess(value=reconstruction_data))
        except Exception as exception:  # pylint: disable=broad-exception-caught
            self._emit(ServiceError(exception=exception))
