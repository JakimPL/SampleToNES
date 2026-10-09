import errno
import os
from pathlib import Path
from typing import Optional, Tuple

from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_application.logic.reconstruction.envelopes import heard_envelopes
from sampletones_application.logic.reconstruction.listening import StemListening
from sampletones_application.logic.reconstruction.session import ReconstructionSession
from sampletones_application.logic.shared.renders import RenderCache
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.view_model.reconstruction.envelopes import (
    ChannelEnvelopesViewModel,
)
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.system.paths import first_missing, is_same_path
from sampletones_shared.utils.system.reveal.selection import open_paths_in_explorer


class ReconstructionManager(CallbackMixin):
    """
    The single authority on which reconstruction is currently loaded.

    - It abstracts two loading modes — file-backed and a project sample's — behind the
      same interface.
    - A project sample is known by its voice id, which the project keeps across a history
      restore and a reopened file, so whoever follows the project finds the voice the open
      document is.
    - Dirty and load state are tracked by a separate session object.
    """

    def __init__(
        self,
        *,
        scheduling: SchedulingBehavior,
        renders: RenderCache,
    ) -> None:
        self._scheduling = scheduling
        self._renders = renders
        self._session: ReconstructionSession = ReconstructionSession()
        self._current_reconstruction: Optional[ReconstructionData] = None
        self._current_features: Optional[ChannelEnvelopesViewModel] = None
        self._voice_id: Optional[str] = None
        self._listening: StemListening = StemListening()

        self.on_reconstruction_loaded: Optional[VoidCallback] = None
        self.on_reconstruction_closed: Optional[VoidCallback] = None

    @property
    def session(self) -> ReconstructionSession:
        return self._session

    @property
    def renders(self) -> RenderCache:
        """Where the audio of the open document is rendered and kept for as long as the screen reads it."""
        return self._renders

    def load_reconstruction(self, path: Path) -> None:
        logger.info(f"Loading reconstruction: {logger.format_path(path)}")
        self._adopt_reconstruction(ReconstructionData.load(path), voice_id=None)
        self._session.mark_loaded(path.name)
        self.call(self.on_reconstruction_loaded)
        logger.info(f"Reconstruction {logger.format_path(path)} loaded successfully")

    def load_reconstruction_object(
        self,
        reconstruction: Reconstruction,
        *,
        name: str,
        voice_id: str,
    ) -> None:
        """Loads a project sample's reconstruction for editing.

        Mirrors :meth:`load_reconstruction` for an object already in memory. The display name is
        supplied by the caller, since a detached reconstruction has no source path to derive it
        from. The document remembers the sample's voice id, which is how an edit finds the sample
        to write back into and how a project change finds the voice the tab shows.
        """
        self._adopt_reconstruction(
            ReconstructionData.from_reconstruction(reconstruction, name=name),
            voice_id=voice_id,
        )
        self._session.mark_loaded(name)
        self.call(self.on_reconstruction_loaded)

    def _adopt_reconstruction(
        self,
        reconstruction_data: ReconstructionData,
        *,
        voice_id: Optional[str],
    ) -> None:
        """Makes ``reconstruction_data`` the open document and refreshes its derived state.

        The reader's listening choice and the cached features track whichever reconstruction is
        open, so every rebinding funnels through here to recompute them in one place. The
        listening is carried onto the new record before the features are read, so the envelopes
        answer for the part the reader is listening to as it now stands. ``voice_id`` names the
        project sample the document is, and ``None`` a standalone document.
        """
        self._current_reconstruction = reconstruction_data
        self._voice_id = voice_id
        self._listening.adopt(reconstruction_data.reconstruction.stems_data)
        self._load_reconstruction_features()

    def _load_reconstruction_features(self) -> None:
        """Reads the envelopes of the part the reader is listening to.

        Raises:
            RuntimeError: If no reconstruction is open to read.
        """
        if self._current_reconstruction is None:
            raise RuntimeError("No reconstruction is loaded when trying to load features")

        reconstruction = self._current_reconstruction.reconstruction
        self._current_features = heard_envelopes(reconstruction, self._listening.selection)

    def refresh_features(self) -> None:
        """Reads the envelopes again after a change to what the reader is listening to.

        A box on the stems card moves which recordings a channel is heard on, and the plot,
        the figures and an export all read from the same envelopes, so they follow it together.
        """
        if self._current_reconstruction is not None:
            self._load_reconstruction_features()

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
        thereby severed from the project: the copy is a distinct object that names no voice, so
        later edits reach only the saved file and leave the sample intact. A failed write leaves
        the open document as it was, still the voice it was.
        """
        if self._current_reconstruction is None:
            return

        self._write_to_file(self._current_reconstruction.reconstruction, filepath)
        self._adopt_reconstruction(
            self._current_reconstruction.detached_copy(filepath),
            voice_id=None,
        )
        self._session.mark_saved(self._current_reconstruction.name)

    @staticmethod
    def _write_to_file(reconstruction: Reconstruction, filepath: Path) -> None:
        reconstruction.save(filepath)
        logger.info(f"Saved reconstruction to: {logger.format_path(filepath)}")

    def detach_current_reconstruction(self) -> None:
        """Re-binds the open reconstruction to its detached, in-memory form.

        Removing the file a standalone document was loaded from leaves the document with no file
        of its own, so it stays open in memory until the reader saves it elsewhere. It keeps the
        same reconstruction object, so live editing continues.
        """
        if self._current_reconstruction is None:
            return

        reconstruction = self._current_reconstruction.reconstruction
        name = self._current_reconstruction.name
        self._current_reconstruction = ReconstructionData.from_reconstruction(
            reconstruction,
            name=name,
        )

    def apply_edited(self, reconstruction: Reconstruction) -> None:
        """Adopts a reconstruction an edit produced.

        The open document rebinds to the fresh reconstruction object and stays the voice it was,
        while the previous object is left untouched for the history to retain.
        """
        if self._current_reconstruction is None:
            return

        self._adopt_reconstruction(
            self._current_reconstruction.with_reconstruction(reconstruction),
            voice_id=self._voice_id,
        )

    def mark_updated(self) -> None:
        self._session.mark_updated()

    def close_reconstruction(self) -> None:
        self._current_reconstruction = None
        self._current_features = None
        self._voice_id = None
        self._listening.release()
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
    def current_features(self) -> Optional[ChannelEnvelopesViewModel]:
        return self._current_features

    @property
    def voice_id(self) -> Optional[str]:
        """The project voice the open document is, or ``None`` for a standalone document or none."""
        return self._voice_id

    @property
    def is_project_sample(self) -> bool:
        """Whether the open document is a sample of the project, whose edits belong to the project."""
        return self._voice_id is not None

    @property
    def listening(self) -> StemListening:
        """Which recordings of the open document the reader is listening to."""
        return self._listening

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

    def is_backed_by(self, path: Path) -> bool:
        """Whether the open document stands for the file at ``path``, however the path is spelled.

        A conversion can write over the file the open document was loaded from or last saved to,
        and removing a file from the browser can take the open document's own away.
        """
        filepath = self.filepath
        return filepath is not None and is_same_path(filepath, path)

    @property
    def source_paths(self) -> Tuple[Path, ...]:
        if self._current_reconstruction is None:
            return ()

        return self._current_reconstruction.reconstruction.audio_filepath
