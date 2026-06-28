from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Self

import numpy as np

from sampletones_application.logic.reconstruction.feature import FeatureData
from sampletones_core.audio import load_audio
from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.logger import logger


@dataclass(frozen=True)
class ReconstructionData:
    config: Config
    reconstruction: Reconstruction
    original_audio: np.ndarray
    feature_data: FeatureData
    filepath: Optional[Path]

    @classmethod
    def load(cls, path: Path) -> Self:
        reconstruction = Reconstruction.load(path)
        return cls._assemble(reconstruction, filepath=path)

    @classmethod
    def from_reconstruction(cls, reconstruction: Reconstruction) -> Self:
        """Wraps an in-memory reconstruction for live-linked editing.

        The reconstruction tab edits the very same object the project sample
        holds, so changes propagate live. Such a sample lives only in memory,
        hence ``filepath`` is ``None``.
        """
        return cls._assemble(
            reconstruction,
            filepath=None,
        )

    @classmethod
    def _assemble(
        cls,
        reconstruction: Reconstruction,
        *,
        filepath: Optional[Path],
    ) -> Self:
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
        except (
            FileNotFoundError,
            IOError,
            IsADirectoryError,
            PermissionError,
            OSError,
        ):
            logger.warning(f"Could not load original audio from '{audio_filepath}'. Using silent audio instead")
            original_audio = np.zeros_like(reconstruction.approximation)

        feature_data = FeatureData.load(reconstruction)

        return cls(
            config=reconstruction.config,
            reconstruction=reconstruction,
            original_audio=original_audio,
            feature_data=feature_data,
            filepath=filepath,
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

        partials: np.ndarray = np.sum(selected_approximations, axis=0)
        return partials
