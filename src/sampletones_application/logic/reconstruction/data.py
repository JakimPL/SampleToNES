from dataclasses import dataclass, replace
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
    name: str
    config: Config
    reconstruction: Reconstruction
    original_audio: np.ndarray
    feature_data: FeatureData
    filepath: Optional[Path]

    @classmethod
    def load(cls, path: Path) -> Self:
        reconstruction = Reconstruction.load(path)
        audio_filepath = reconstruction.audio_filepath
        name = audio_filepath.stem if audio_filepath is not None else path.stem
        return cls._assemble(reconstruction, filepath=path, name=name)

    @classmethod
    def from_reconstruction(cls, reconstruction: Reconstruction, *, name: str) -> Self:
        """Wraps an in-memory reconstruction for live-linked editing.

        The reconstruction tab edits the very same object the project sample
        holds, so changes propagate live. Such a sample lives only in memory,
        hence ``filepath`` is ``None`` and its display name is supplied by the
        caller (the project sample's name) rather than derived from a file path.
        """
        return cls._assemble(
            reconstruction,
            filepath=None,
            name=name,
        )

    def with_reconstruction(self, reconstruction: Reconstruction) -> Self:
        """Rebinds this data to an edited reconstruction, keeping name and origin.

        A regeneration produces a fresh reconstruction object; the display name,
        file location and source audio are unchanged, so only the reconstruction
        and its derived features are refreshed.
        """
        return replace(
            self,
            reconstruction=reconstruction,
            config=reconstruction.config,
            feature_data=FeatureData.load(reconstruction),
        )

    @classmethod
    def _assemble(
        cls,
        reconstruction: Reconstruction,
        *,
        filepath: Optional[Path],
        name: str,
    ) -> Self:
        original_audio = cls._load_original_audio(reconstruction)
        feature_data = FeatureData.load(reconstruction)

        return cls(
            config=reconstruction.config,
            reconstruction=reconstruction,
            original_audio=original_audio,
            feature_data=feature_data,
            filepath=filepath,
            name=name,
        )

    @staticmethod
    def _load_original_audio(reconstruction: Reconstruction) -> np.ndarray:
        """Loads the source audio, falling back to silence when it is detached or unreadable.

        A reconstruction detached from its origin (a project sample) carries no source path, and a
        file-backed reconstruction may point at audio absent on this machine. In both cases the
        approximation still plays; only the original-audio comparison is silent.
        """
        audio_filepath = reconstruction.audio_filepath
        if audio_filepath is None:
            return np.zeros_like(reconstruction.approximation)

        config = reconstruction.config
        try:
            return load_audio(
                path=audio_filepath,
                target_sample_rate=config.library.sample_rate,
                normalize=config.general.normalize,
                quantize=config.general.quantize,
            )
        except (
            FileNotFoundError,
            IOError,
            IsADirectoryError,
            PermissionError,
            OSError,
        ):
            logger.warning(f"Could not load original audio from '{audio_filepath}'. Using silent audio instead")
            return np.zeros_like(reconstruction.approximation)

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
