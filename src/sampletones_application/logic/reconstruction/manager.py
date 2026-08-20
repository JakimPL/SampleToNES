import errno
import os
from pathlib import Path
from typing import Optional, Tuple

from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_application.logic.reconstruction.feature import FeatureData
from sampletones_application.logic.reconstruction.session import ReconstructionSession
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.serialization import hash_model
from sampletones_shared.utils.system.paths import first_missing
from sampletones_shared.utils.system.reveal.selection import open_paths_in_explorer


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
        logger.info(f"Loading reconstruction: {logger.format_path(path)}")
        self._adopt_reconstruction(ReconstructionData.load(path))
        self._session.mark_loaded(path.name)
        self.call(self.on_reconstruction_loaded)
        logger.info(f"Reconstruction {logger.format_path(path)} loaded successfully")

    def load_reconstruction_object(
        self,
        reconstruction: Reconstruction,
        *,
        name: str,
    ) -> None:
        """Loads an in-memory reconstruction (e.g. a project sample's) for editing.

        Mirrors :meth:`load_reconstruction` for an object already in memory, so edits
        made in the reconstruction tab mutate the same instance the caller holds. The
        display name is supplied by the caller, since a detached reconstruction has no
        source path to derive it from.
        """
        self._adopt_reconstruction(
            ReconstructionData.from_reconstruction(reconstruction, name=name),
        )
        self._session.mark_loaded(name)
        self.call(self.on_reconstruction_loaded)

    def _adopt_reconstruction(self, reconstruction_data: ReconstructionData) -> None:
        """Makes ``reconstruction_data`` the open document and refreshes its derived state.

        The coefficient and cached features track whichever reconstruction is open, so every
        rebinding funnels through here to recompute them in one place.
        """
        self._current_reconstruction = reconstruction_data
        self._coefficient = reconstruction_data.reconstruction.coefficient
        self._load_reconstruction_features()

    def _load_reconstruction_features(self) -> None:
        if self._current_reconstruction is None:
            raise RuntimeError("No reconstruction is loaded when trying to load features")

        reconstruction = self._current_reconstruction.reconstruction
        feature_data = FeatureData.load(reconstruction)
        self._current_features = feature_data
        self._reconstruction_hash = hash_model(reconstruction)

    def save_reconstruction(self, filepath: Optional[Path] = None) -> bool:
        """Writes the open reconstruction to disk, reporting whether the write happened.

        A reconstruction with neither a supplied nor a stored file path stays in memory and needs
        'Save as' to choose one, so the call reports that nothing was written.
        """
        if not self._current_reconstruction:
            return False

        target_path = filepath or self._current_reconstruction.filepath
        if target_path is None:
            logger.warning("Reconstruction has no file path; use 'Save as' to choose one")
            return False

        self._write_to_file(
            self._current_reconstruction.reconstruction,
            target_path,
        )
        self._session.mark_saved(filepath.name if filepath is not None else None)
        return True

    def save_reconstruction_as(self, filepath: Path) -> None:
        """Saves the open reconstruction to a chosen file and adopts it as a standalone document.

        The write happens first; on success the open document rebinds to an independent,
        file-backed copy anchored at ``filepath``. A reconstruction that was a project sample is
        thereby severed from the project: the copy is a distinct object, so later edits reach only
        the saved file and leave the sample intact. A failed write leaves the open document as is.
        """
        if self._current_reconstruction is None:
            return

        self._write_to_file(self._current_reconstruction.reconstruction, filepath)
        self._adopt_reconstruction(self._current_reconstruction.detached_copy(filepath))
        self._session.mark_saved(self._current_reconstruction.name)

    @staticmethod
    def _write_to_file(reconstruction: Reconstruction, filepath: Path) -> None:
        reconstruction.save(filepath)
        logger.info(f"Saved reconstruction to: {logger.format_path(filepath)}")

    def detach_current_reconstruction(self) -> None:
        """Re-binds the open reconstruction to its detached, in-memory form.

        Adding a file-backed reconstruction to the sequencer turns it into a project sample: its
        source audio is detached and it maps to no standalone file. The open document adopts that
        form so the reconstruction view reflects the owned sample, keeping the same reconstruction
        object so live editing continues.
        """
        if self._current_reconstruction is None:
            return

        reconstruction = self._current_reconstruction.reconstruction
        name = self._current_reconstruction.name
        self._current_reconstruction = ReconstructionData.from_reconstruction(
            reconstruction,
            name=name,
        )

    def apply_regenerated(self, reconstruction: Reconstruction) -> None:
        """Adopts an edited reconstruction produced by regeneration.

        The open document rebinds to the fresh reconstruction object so the editor
        and any owning project sample continue to share one identity, while the
        previous object is left untouched for the history to retain.
        """
        if self._current_reconstruction is None:
            return

        self._adopt_reconstruction(self._current_reconstruction.with_reconstruction(reconstruction))

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
            priority=self._scheduling.priorities.schedule,
        )

    def locate_original_audio(self) -> None:
        original_audio_paths = self.source_paths
        if not original_audio_paths:
            return

        missing_path = first_missing(original_audio_paths)
        if missing_path is not None:
            raise FileNotFoundError(
                errno.ENOENT,
                os.strerror(errno.ENOENT),
                str(missing_path),
            )

        open_paths_in_explorer(original_audio_paths)

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
    def is_file_backed(self) -> bool:
        return self.filepath is not None

    @property
    def source_paths(self) -> Tuple[Path, ...]:
        if self._current_reconstruction is None:
            return ()

        return self._current_reconstruction.reconstruction.source_paths
