from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, Self, Tuple

from sampletones_application.logic.main.sources.key import SourceKey
from sampletones_application.logic.main.sources.recording import Recording


@dataclass(frozen=True)
class Folder:
    """A directory a reader gathered, standing for the recordings found below it.

    This is where the folder relation lives: a recording states its own path and its settings, and
    the folder holding it is what says a run mirrors that folder's tree for it. A recording taken
    out of a folder is a loose recording, with nothing left over to say otherwise.
    """

    root: Path
    recordings: Tuple[Recording, ...]

    @property
    def key(self) -> SourceKey:
        return SourceKey.folder(self.root)

    @property
    def count(self) -> int:
        return len(self.recordings)

    def with_recordings(self, recordings: Iterable[Recording]) -> Self:
        return replace(self, recordings=tuple(recordings))
