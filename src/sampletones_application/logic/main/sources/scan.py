import threading
from pathlib import Path
from typing import Callable, Final, List, Optional, Tuple

from sampletones_application.utils.parallelization.thread import concurrent
from sampletones_core.reconstructions.converter.paths import is_audio_file, walk_entries
from sampletones_shared.types.callback import PathCallback, VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin

CountCallback = Callable[[int], None]
FoundCallback = Callable[[Path, Tuple[Path, ...]], None]

REPORT_EVERY: Final[int] = 64
REPORT_DUE: Final[int] = 0


class FolderScan(CallbackMixin):
    """The recordings below a folder, read beside the interface rather than in front of it.

    A folder a reader points at holds a handful of recordings or a disk's worth, and finding out
    costs what the tree costs — seconds where the tree is large. The walk therefore runs on a
    worker, reports how many it has met as it goes, and stops when the reader asks it to, so the
    window keeps answering and the reader knows what it is waiting for.

    The reports arrive on the worker's own thread, so whoever draws from them crosses to the
    thread DearPyGui's context belongs to.
    """

    def __init__(self) -> None:
        self._stopping = threading.Event()
        self._running = threading.Event()

        self.on_started: Optional[PathCallback] = None
        self.on_progress: Optional[CountCallback] = None
        self.on_stopped: Optional[VoidCallback] = None

    @property
    def running(self) -> bool:
        """A walk is under way, which is what the reader is being shown."""
        return self._running.is_set()

    def start(self, root: Path, answer: FoundCallback) -> None:
        """Reads what ``root`` holds and hands it to ``answer``, counting as the walk goes.

        The answer travels with the walk that earns it, so the same scan serves a gathering and a
        conversion and each hears back from its own reading. One walk runs at a time: a folder
        asked for while another is being read is turned away, and asking again once the window
        closes reads it.
        """
        if self.running:
            return

        self._stopping.clear()
        self._running.set()
        self.call(self.on_started, root)
        self._walk(root, answer)

    def stop(self) -> None:
        """Asks the walk to give up, which it does at the next recording it meets."""
        self._stopping.set()

    @concurrent(wait=False)
    def _walk(self, root: Path, answer: FoundCallback) -> None:
        """Reads the tree, reports how it ended, and lets the walk go, in that order.

        The walk holds its claim until its report has gone out, so the worker and the scan agree
        on the moment a folder may next be asked for. It is let go whatever becomes of the reading,
        so one that fails partway leaves the next folder free to be asked for.
        """
        try:
            found = self._gather(root)
            if self._stopping.is_set():
                self.call(self.on_stopped)
                return

            self.call(answer, root, tuple(sorted(found)))
        finally:
            self._running.clear()

    def _gather(self, root: Path) -> List[Path]:
        """The recordings met below ``root``, giving up at the entry the reader stops the walk on.

        Every entry the tree holds is offered, so a folder of thousands holding a handful of
        recordings answers **Stop** as promptly as one holding thousands.
        """
        found: List[Path] = []
        for path in walk_entries(root):
            if self._stopping.is_set():
                return found

            if not is_audio_file(path):
                continue

            found.append(path)
            if len(found) % REPORT_EVERY == REPORT_DUE:
                self.call(self.on_progress, len(found))

        return found
