from pathlib import Path
from typing import List, Self

import numpy as np
from pydantic import BaseModel, ConfigDict

from sampletones.audio import load_audio
from sampletones.configs import Config
from sampletones.constants.enums import GeneratorName
from sampletones.reconstruction import Reconstruction
from sampletones.utils.logger import logger

from .feature import FeatureData


class ReconstructionData(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    config: Config
    reconstruction: Reconstruction
    original_audio: np.ndarray
    feature_data: FeatureData

    @classmethod
    def load(cls, path: Path) -> Self:
        reconstruction = Reconstruction.load_and_validate(path)
        audio_filepath = reconstruction.audio_filepath
        sample_rate = reconstruction.config.library.sample_rate
        normalize = reconstruction.config.general.normalize
        quantize = reconstruction.config.general.quantize

        try:
            original_audio = load_audio(
                path=audio_filepath,
                target_sample_rate=sample_rate,
                normalize=normalize,
                quantize=quantize,
            )
        except (IOError, FileNotFoundError, IsADirectoryError, OSError, PermissionError):
            logger.warning(f"Could not load original audio from {audio_filepath}. Using silent audio instead")
            original_audio = np.zeros_like(reconstruction.approximation)

        feature_data = FeatureData.load(reconstruction)

        return cls(
            config=reconstruction.config,
            reconstruction=reconstruction,
            original_audio=original_audio,
            feature_data=feature_data,
        )

    def get_partials(self, generator_names: List[GeneratorName]) -> np.ndarray:
        if not generator_names:
            return np.zeros_like(self.original_audio)

        selected_approximations = [
            self.reconstruction.approximations[generator_name]
            for generator_name in generator_names
            if generator_name in self.reconstruction.approximations
        ]

        if not selected_approximations:
            return np.zeros_like(self.original_audio)

        return np.sum(selected_approximations, axis=0)
