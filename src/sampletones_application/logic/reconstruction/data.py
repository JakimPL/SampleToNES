from dataclasses import dataclass, replace
from pathlib import Path
from typing import List, Optional, Self

import numpy as np

from sampletones_application.logic.reconstruction.feature import FeatureData
from sampletones_application.view_model.shared.waveform_data import WaveformData
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
    original_audio: Optional[np.ndarray]
    feature_data: FeatureData
    filepath: Optional[Path]

    @classmethod
    def load(cls, path: Path) -> Self:
        reconstruction = Reconstruction.load(path)
        return cls._assemble(
            reconstruction,
            filepath=path,
            name=cls._derive_name(reconstruction, path),
        )

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

    def detached_copy(self, filepath: Path) -> Self:
        """Builds an independent, file-backed copy of this data anchored at ``filepath``.

        Save As writes the reconstruction to its own file and adopts this copy as the open
        document. The copy owns a fresh reconstruction object, so a document that was a project
        sample becomes a standalone entity: later edits reach only the saved file, leaving the
        project's sample unchanged. The already-loaded original audio is reused, since the copy
        shares the same source.
        """
        reconstruction = self.reconstruction.model_copy(deep=True)
        return replace(
            self,
            reconstruction=reconstruction,
            config=reconstruction.config,
            feature_data=FeatureData.load(reconstruction),
            filepath=filepath,
            name=self._derive_name(reconstruction, filepath),
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
    def _derive_name(reconstruction: Reconstruction, filepath: Path) -> str:
        """Names the document after its source audio when present, otherwise after the file.

        A file-backed reconstruction keeps the audio's name for display and export; a detached
        reconstruction (no source audio) falls back to the ``.stn`` filename.
        """
        audio_filepath = reconstruction.audio_filepath
        return audio_filepath.stem if audio_filepath is not None else filepath.stem

    @staticmethod
    def _load_original_audio(reconstruction: Reconstruction) -> Optional[np.ndarray]:
        """Loads the source audio, yielding ``None`` when no usable original exists.

        A reconstruction detached from its origin (a project sample) records no source path, and a
        file-backed reconstruction may point at audio absent or unreadable on this machine. Both
        cases yield ``None``; the approximation then stands on its own in playback and the display.
        """
        audio_filepath = reconstruction.audio_filepath
        if audio_filepath is None:
            return None

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
            logger.warning(f"Could not load original audio from '{audio_filepath}'. The original is unavailable")
            return None

    def waveform_data(self) -> WaveformData:
        """Projects the slice of this data the waveform display renders."""
        return WaveformData(
            original_audio=self.original_audio,
            approximation=self.reconstruction.approximation,
            approximations=dict(self.reconstruction.approximations),
            coefficient=self.reconstruction.coefficient,
            frame_length=self.reconstruction.config.frame_length,
        )

    def get_partials(self, generator_names: List[GeneratorName]) -> np.ndarray:
        return self.waveform_data().partials(generator_names)
