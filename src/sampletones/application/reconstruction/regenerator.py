from typing import Callable, List, Optional, cast

import numpy as np

from sampletones.constants.enums import FeatureKey, GeneratorName
from sampletones.exporters import GENERATOR_NAME_TO_EXPORTER_MAP, Features
from sampletones.generators import GeneratorUnion
from sampletones.instructions import InstructionUnion

from ..utils.thread import concurrent
from .data import ReconstructionData

OnRegenerationFinished = Callable[[ReconstructionData], None]


class Regenerator:
    def __init__(self) -> None:
        self.reconstruction_data: Optional[ReconstructionData] = None

        self._on_regeneration_finished: Optional[OnRegenerationFinished] = None

    @concurrent(wait=False, method_bound=False)
    def regenerate(
        self,
        generator_name: GeneratorName,
        features: Features,
        feature_key: FeatureKey,
        data: np.ndarray,
    ) -> None:
        if self.reconstruction_data is None:
            raise RuntimeError("No reconstruction available to regenerate.")

        config = self.reconstruction_data.config
        exporter_class = GENERATOR_NAME_TO_EXPORTER_MAP[generator_name]
        generator_class = exporter_class.get_generator_type()
        features[feature_key] = data

        instructions = cast(List[InstructionUnion], exporter_class.from_features(features))
        generator = generator_class(config, generator_name)
        audio = self._generate_generator_audio(generator, instructions)

        self.reconstruction_data.reconstruction.update_generator_data(generator_name, instructions, audio)
        if self._on_regeneration_finished is not None:
            self._on_regeneration_finished(self.reconstruction_data)

    def _generate_generator_audio(
        self,
        generator: GeneratorUnion,
        instructions: List[InstructionUnion],
    ) -> np.ndarray:
        return np.concatenate([generator(instruction) for instruction in instructions])  # type: ignore

    def set_callbacks(self, on_regeneration_finished: Optional[OnRegenerationFinished] = None) -> None:
        if on_regeneration_finished is not None:
            self._on_regeneration_finished = on_regeneration_finished
