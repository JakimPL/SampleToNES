from pathlib import Path
from typing import Optional

from sampletones_application.layout.behavior import SchedulingBehavior
from sampletones_application.logic.reconstruction.session import ReconstructionSession
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
    """Owns the currently loaded reconstruction and its session state.

    The reconstruction manager is the single point of truth for which
    reconstruction is open.  It handles both file-backed reconstructions
    (``load_reconstruction``) and in-memory ones borrowed from a project sample
    (``load_reconstruction_object``), so that edits in the Reconstructions tab
    always mutate the same object the caller holds — no copy is made.

    Responsibilities:
    - Load, save, and close the current :class:`~sampletones_core.reconstructions.Reconstruction`.
    - Wrap the raw reconstruction in :class:`~sampletones_application.view_model.reconstruction.data.ReconstructionData`
      and compute :class:`~sampletones_application.view_model.reconstruction.feature.FeatureData`
      for graph display.
    - Maintain a :class:`~sampletones_application.logic.reconstruction.session.ReconstructionSession`
      tracking load/dirty/saved state.
    - Fire ``on_reconstruction_loaded`` and ``on_reconstruction_closed`` callbacks
      (via ``CallbackMixin``) so that the coordinator can react to lifecycle events.

    Governing principles:
    - No DPG.  No imports from ``ui/``, ``view_model/`` (except to construct
      ``ReconstructionData`` / ``FeatureData``), or ``coordinators/``.
    - ``close_reconstruction`` posts ``on_reconstruction_closed`` through
      ``CallbackQueue`` rather than calling it directly, to guarantee it runs
      on the main thread even if ``close`` is triggered from a background path.
    - ``mark_updated()`` is called by external coordinators after a regeneration
      completes; it does not reload features — the coordinator is responsible
      for refreshing the display separately.

    Dependencies: ``ReconstructionSession``, ``ReconstructionData``,
    ``FeatureData``, ``CallbackQueue``, ``CallbackMixin``.
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

    def load_reconstruction(self, filepath: Path) -> None:
        if filepath.is_dir():
            raise IsADirectoryError(f"Expected a file but got a directory: {filepath}")

        if not filepath.exists():
            raise FileNotFoundError(f"Reconstruction file not found: {filepath}")

        self._load_reconstruction_data(filepath)
        self._load_reconstruction_features()
        self._session.mark_loaded(filepath.stem)
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
