from dataclasses import dataclass, replace
from pathlib import Path
from typing import Self, Tuple

from sampletones_application.logic.main.sources.key import SourceKey
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings


@dataclass(frozen=True)
class Recording:
    """One audio file a run converts, together with the settings it converts under.

    The settings are the value the core records as the stem's own, so what a reader edits in the
    list is what the reconstruction carries. A recording states its own path and nothing about
    where it was gathered from: the folder holding it is what knows that.
    """

    path: Path
    settings: StemSettings

    @property
    def key(self) -> SourceKey:
        return SourceKey.recording(self.path)

    @property
    def recordings(self) -> Tuple[Self, ...]:
        """The recordings this row stands for, which for one recording is itself."""
        return (self,)

    @property
    def count(self) -> int:
        return 1

    def with_settings(self, settings: StemSettings) -> Self:
        return replace(self, settings=settings)
