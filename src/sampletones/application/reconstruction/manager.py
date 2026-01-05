from pathlib import Path
from typing import Optional

from sampletones.application.constants.general import VAL_PRIORITY_SCHEDULE
from sampletones.reconstructions import Reconstruction
from sampletones.typehints import VoidCallback
from sampletones.utils import hash_model
from sampletones.utils.callbacks import CallbackMixin
from sampletones.utils.logger import logger

from ..utils.callbacks.queue import CallbackQueue
from .data import ReconstructionData
from .feature import FeatureData


class ReconstructionManager(CallbackMixin):
    def __init__(self):
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

    def save_reconstruction(self) -> None:
        if not self.current_reconstruction:
            return

        reconstruction = self.current_reconstruction.reconstruction
        reconstruction.save(self.current_reconstruction.filepath)
        logger.info(f"Saved reconstruction to: {logger.format_path(self.current_reconstruction.filepath)}")

    def close_reconstruction(self) -> None:
        self.current_reconstruction = None
        self.current_features = None
        self.reconstruction_hash = ""
        self.coefficient = 1.0
        CallbackQueue.add(self.call, self.on_reconstruction_closed, priority=VAL_PRIORITY_SCHEDULE)

    @property
    def reconstruction(self) -> Optional[Reconstruction]:
        if self.current_reconstruction is None:
            return None

        return self.current_reconstruction.reconstruction
