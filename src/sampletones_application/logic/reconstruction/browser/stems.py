import threading
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from sampletones_application.logic.reconstruction.ownership import recording_names
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.parallelization.coalescing import LatestWinsExecutor
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.exceptions import SampleToNESError
from sampletones_shared.logger import logger
from sampletones_shared.utils.callbacks import CallbackMixin

RecordingsCallback = Callable[[Path, Tuple[str, ...]], None]


@dataclass(frozen=True)
class _ReadRecordings:
    """What one reading of a document found, held against the state of the file it was read from."""

    modified_at: Optional[float]
    names: Tuple[str, ...]


class ReconstructionStemsReader(CallbackMixin):
    """Answers which recordings a reconstruction on disk is made of, reading each document once.

    A row names a file, and only the file says what it holds, so the answer costs a read. The read
    runs on a worker and the answer is kept against the moment the file was last written, which
    makes a row asked about again answer at once and a regenerated document read afresh. A pointer
    crossing many rows leaves the read of the row it comes to rest on, since a request replaces the
    one still waiting.

    ``on_recordings_read`` announces an answer on the render thread, for the questions the reading
    outlived. A document that cannot be read answers with nothing, which leaves whoever asked with
    nothing to show.
    """

    def __init__(self) -> None:
        self.on_recordings_read: Optional[RecordingsCallback] = None

        self._executor = LatestWinsExecutor()
        self._lock = threading.Lock()
        self._read: Dict[Path, _ReadRecordings] = {}

    def recordings(self, path: Path) -> Optional[Tuple[str, ...]]:
        """The recordings the document names, in record order, and ``None`` while it stands unread.

        Asking for an unread document starts the reading that answers it, so one call both says
        what is known and sets about learning the rest.

        Args:
            path: The reconstruction file the row names.

        Returns:
            Optional[Tuple[str, ...]]: The recordings, or None until the reading lands.
        """
        modified_at = self._modified_at(path)
        with self._lock:
            read = self._read.get(path)

        if read is not None and read.modified_at == modified_at:
            return read.names

        self._executor.submit(partial(self._read_document, path, modified_at))
        return None

    def _read_document(self, path: Path, modified_at: Optional[float]) -> None:
        names = self._recordings_of(path)
        with self._lock:
            self._read[path] = _ReadRecordings(modified_at=modified_at, names=names)

        CallbackQueue.add(self._announce, path, names)

    def _announce(self, path: Path, names: Tuple[str, ...]) -> None:
        self.call(self.on_recordings_read, path, names)

    @staticmethod
    def _recordings_of(path: Path) -> Tuple[str, ...]:
        """The recordings the document at ``path`` names, and nothing where it cannot be read."""
        try:
            stems_data = Reconstruction.read_stems_data(path)
        except (OSError, SampleToNESError) as exception:
            logger.debug(f'Failed to read the recordings of "{path}": {exception}')
            return ()

        return recording_names(stems_data)

    @staticmethod
    def _modified_at(path: Path) -> Optional[float]:
        """When the file was last written, and nothing where the disk does not answer for it."""
        try:
            return path.stat().st_mtime
        except OSError:
            return None
