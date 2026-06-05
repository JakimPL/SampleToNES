from pathlib import Path
from typing import Optional

from sampletones_application.layout.behavior import SchedulingBehavior
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.view_model.reconstruction.data import ReconstructionData
from sampletones_application.view_model.reconstruction.feature import FeatureData
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.serialization import hash_model
from sampletones_shared.utils.system.paths import open_path_in_explorer


class ReconstructionManager(CallbackMixin):
    def __init__(self, *, scheduling: SchedulingBehavior) -> None:
        self._scheduling = scheduling
        self._current_reconstruction: Optional[ReconstructionData] = None
        self._current_features: Optional[FeatureData] = None
        self._reconstruction_hash: str = ""
        self._coefficient: float = 1.0

        self.on_reconstruction_loaded: Optional[VoidCallback] = None
        self.on_reconstruction_closed: Optional[VoidCallback] = None

    def load_reconstruction(self, filepath: Path) -> None:
        if filepath.is_dir():
            raise IsADirectoryError(f"Expected a file but got a directory: {filepath}")

        if not filepath.exists():
            raise FileNotFoundError(f"Reconstruction file not found: {filepath}")

        self._load_reconstruction_data(filepath)
        self._load_reconstruction_features()
        self.call(self.on_reconstruction_loaded)

    def load_reconstruction_object(self, reconstruction: Reconstruction) -> None:
        """Loads an in-memory reconstruction (e.g. a project sample's) for editing.

        Mirrors :meth:`load_reconstruction` but wraps an existing object instead of
        reading a file, so edits made in the reconstruction tab mutate the same
        instance the caller holds.
        """
        self._current_reconstruction = ReconstructionData.from_reconstruction(reconstruction)
        self._coefficient = reconstruction.coefficient
        self._load_reconstruction_features()
        self.call(self.on_reconstruction_loaded)

    def _load_reconstruction_data(self, filepath: Path) -> None:
        self._current_reconstruction = ReconstructionData.load(filepath)
        self._coefficient = self._current_reconstruction.reconstruction.coefficient

    def _load_reconstruction_features(self) -> None:
        if self._current_reconstruction is None:
            raise RuntimeError("No reconstruction is loaded when trying to load features")

        reconstruction = self._current_reconstruction.reconstruction
        feature_data = FeatureData.load(reconstruction)
        self._current_features = feature_data
        self._reconstruction_hash = hash_model(reconstruction)

    def is_reconstruction_loaded(self) -> bool:
        return self._current_reconstruction is not None

    def save_reconstruction(self, filepath: Optional[Path] = None) -> None:
        if not self._current_reconstruction:
            return

        reconstruction = self._current_reconstruction.reconstruction
        target_path = filepath or self._current_reconstruction.filepath
        reconstruction.save(target_path)
        logger.info(f"Saved reconstruction to: {logger.format_path(target_path)}")

    def close_reconstruction(self) -> None:
        self._current_reconstruction = None
        self._current_features = None
        self._reconstruction_hash = ""
        self._coefficient = 1.0
        CallbackQueue.add(
            self.call,
            self.on_reconstruction_closed,
            priority=self._scheduling.priority_schedule,
        )

    def locate_original_audio(self) -> None:
        original_audio_path = self.audio_filepath
        if not original_audio_path:
            return

        if not original_audio_path.exists():
            raise FileNotFoundError(f"Original audio file '{original_audio_path}' could not be found.")

        open_path_in_explorer(original_audio_path)

    @property
    def current_reconstruction(self) -> Optional[ReconstructionData]:
        return self._current_reconstruction

    @property
    def current_features(self) -> Optional[FeatureData]:
        return self._current_features

    @property
    def reconstruction(self) -> Optional[Reconstruction]:
        if self._current_reconstruction is None:
            return None

        return self._current_reconstruction.reconstruction

    @property
    def filepath(self) -> Optional[Path]:
        if self._current_reconstruction is None:
            return None

        return self._current_reconstruction.filepath

    @property
    def audio_filepath(self) -> Optional[Path]:
        if self._current_reconstruction is None:
            return None

        return self._current_reconstruction.reconstruction.audio_filepath
