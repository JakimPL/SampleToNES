from pathlib import Path
from typing import Optional

from sampletones_application.constants.general import VAL_PRIORITY_SCHEDULE
from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_application.logic.reconstruction.feature import FeatureData
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.serialization import hash_model
from sampletones_shared.utils.system.paths import open_path_in_explorer


class ReconstructionManager(CallbackMixin):
    def __init__(self) -> None:
        self.current_reconstruction: Optional[ReconstructionData] = None
        self.current_features: Optional[FeatureData] = None
        self.reconstruction_hash: str = ""
        self.coefficient: float = 1.0

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

    def _load_reconstruction_data(self, filepath: Path) -> None:
        self.current_reconstruction = ReconstructionData.load(filepath)
        self.coefficient = self.current_reconstruction.reconstruction.coefficient

    def _load_reconstruction_features(self) -> None:
        if self.current_reconstruction is None:
            raise RuntimeError("No reconstruction is loaded when trying to load features")

        reconstruction = self.current_reconstruction.reconstruction
        feature_data = FeatureData.load(reconstruction)
        self.current_features = feature_data
        self.reconstruction_hash = hash_model(reconstruction)

    def is_reconstruction_loaded(self) -> bool:
        return self.current_reconstruction is not None

    def save_reconstruction(self, filepath: Optional[Path] = None) -> None:
        if not self.current_reconstruction:
            return

        reconstruction = self.current_reconstruction.reconstruction
        target_path = filepath or self.current_reconstruction.filepath
        reconstruction.save(target_path)
        logger.info(f"Saved reconstruction to: {logger.format_path(target_path)}")

    def close_reconstruction(self) -> None:
        self.current_reconstruction = None
        self.current_features = None
        self.reconstruction_hash = ""
        self.coefficient = 1.0
        CallbackQueue.add(self.call, self.on_reconstruction_closed, priority=VAL_PRIORITY_SCHEDULE)

    def locate_original_audio(self) -> None:
        original_audio_path = self.audio_filepath
        if not original_audio_path:
            return

        if not original_audio_path.exists():
            raise FileNotFoundError(f"Original audio file '{original_audio_path}' could not be found.")

        open_path_in_explorer(original_audio_path)

    @property
    def reconstruction(self) -> Optional[Reconstruction]:
        if self.current_reconstruction is None:
            return None

        return self.current_reconstruction.reconstruction

    @property
    def filepath(self) -> Optional[Path]:
        if self.current_reconstruction is None:
            return None

        return self.current_reconstruction.filepath

    @property
    def audio_filepath(self) -> Optional[Path]:
        if self.current_reconstruction is None:
            return None

        return self.current_reconstruction.reconstruction.audio_filepath
