from typing import Callable, List, Optional, cast

import numpy as np

from sampletones_application.constants.general import VAL_PRIORITY_SCHEDULE
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.thread import concurrent
from sampletones_application.view_model.reconstruction.data import ReconstructionData
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.exporters import GENERATOR_NAME_TO_EXPORTER_MAP, Features
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion
from sampletones_core.types.feature import FeatureValue
from sampletones_shared.utils.callbacks import CallbackMixin

OnRegenerationFinished = Callable[[ReconstructionData], None]


class Regenerator(CallbackMixin):
    def __init__(self, reconstruction_manager: ReconstructionManager) -> None:
        self.reconstruction_manager = reconstruction_manager

        self.on_regeneration_finished: Optional[OnRegenerationFinished] = None

    @concurrent(wait=False, method_bound=False)
    def regenerate(
        self,
        generator_name: GeneratorName,
        features: Features,
        feature_key: FeatureKey,
        data: FeatureValue,
    ) -> None:
        if self.reconstruction_data is None:
            raise RuntimeError("No reconstruction available to regenerate")

        config = self.reconstruction_data.config
        exporter_class = GENERATOR_NAME_TO_EXPORTER_MAP[generator_name]
        generator_class = exporter_class.get_generator_type()
        features[feature_key] = data

        instructions = cast(List[InstructionUnion], exporter_class.from_features(features))
        generator = generator_class(config, generator_name)
        audio = self._generate_generator_audio(generator, instructions)

        self.reconstruction_data.reconstruction.update_generator_data(generator_name, instructions, audio)
        CallbackQueue.add(self.call, self.on_regeneration_finished, priority=VAL_PRIORITY_SCHEDULE)

    def _generate_generator_audio(
        self,
        generator: GeneratorUnion,
        instructions: List[InstructionUnion],
    ) -> np.ndarray:
        return np.concatenate([generator(instruction, save=True) for instruction in instructions])  # type: ignore

    @property
    def reconstruction_data(self) -> Optional[ReconstructionData]:
        return self.reconstruction_manager._current_reconstruction
