from pathlib import Path
from typing import Optional

from sampletones_application.layout.behavior import SchedulingBehavior
from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_application.logic.reconstruction.feature import FeatureData
from sampletones_application.logic.reconstruction.session import ReconstructionSession
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.serialization import hash_model
from sampletones_shared.utils.system.paths import open_path_in_explorer


class ReconstructionManager(CallbackMixin):
    """
    The single authority on which reconstruction is currently loaded.

    - It abstracts two loading modes — file-backed and in-memory — behind the
      same interface.
    - For the in-memory case, edits mutate the original object by identity;
      no copy is made.
    - Dirty and load state are tracked by a separate session object.
    """

    def __init__(self, *, scheduling: SchedulingBehavior) -> None:
        self._scheduling = scheduling
        self._session: ReconstructionSession = ReconstructionSession()
        self._current_reconstruction: Optional[ReconstructionData] = None
        self._current_features: Optional[FeatureData] = None
        self._reconstruction_hash: str = ""
        self._coefficient: float = 1.0

        self.on_reconstruction_loaded: Optional[VoidCallback] = None
        self.on_reconstruction_closed: Optional[VoidCallback] = None

    @property
    def session(self) -> ReconstructionSession:
        return self._session

    def load_reconstruction(self, path: Path) -> None:
        logger.info(f"Loading project: {logger.format_path(path)}")
        self._load_reconstruction_data(path)
        self._load_reconstruction_features()
        self._session.mark_loaded(path.stem)
        self.call(self.on_reconstruction_loaded)
        logger.info(f"Reconstruction {logger.format_path(path)} loaded successfully")

    def load_reconstruction_object(self, reconstruction: Reconstruction) -> None:
        """Loads an in-memory reconstruction (e.g. a project sample's) for editing.

        Mirrors :meth:`load_reconstruction` for an object already in memory, so edits
        made in the reconstruction tab mutate the same instance the caller holds.
        """
        self._current_reconstruction = ReconstructionData.from_reconstruction(reconstruction)
        self._coefficient = reconstruction.coefficient
        self._load_reconstruction_features()
        self._session.mark_loaded(reconstruction.audio_filepath.stem)
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

    def save_reconstruction(self, filepath: Optional[Path] = None) -> None:
        if not self._current_reconstruction:
            return

        reconstruction = self._current_reconstruction.reconstruction
        target_path = filepath or self._current_reconstruction.filepath
        if target_path is None:
            logger.warning("Reconstruction has no file path; use 'Save as' to choose one")
            return

        reconstruction.save(target_path)
        logger.info(f"Saved reconstruction to: {logger.format_path(target_path)}")
        self._session.mark_saved(filepath.stem if filepath is not None else None)

    def mark_updated(self) -> None:
        self._session.mark_updated()

    def close_reconstruction(self) -> None:
        self._current_reconstruction = None
        self._current_features = None
        self._reconstruction_hash = ""
        self._coefficient = 1.0
        self._session.mark_closed()
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
