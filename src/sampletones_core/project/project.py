from __future__ import annotations

from typing import Optional

from sampletones_core.data import Metadata
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.structures import IdentifiedCollection
from sampletones_shared.constants.project import (
    DEFAULT_PROJECT_AUTHOR,
    DEFAULT_PROJECT_COMMENT,
    DEFAULT_PROJECT_TITLE,
    DEFAULT_ROWS_PER_PATTERN,
)

from .info import ProjectInfo
from .settings import ProjectSettings
from .song import Song


class Project:
    """The top-level container for everything a user composes.

    Owns the samples (each embedding its own reconstruction) and the song
    arrangement. References inside the song point at samples by their stable
    ``id``; the :class:`IdentifiedCollection` resolves those ids in O(1) while
    also exposing reorder-safe positions for the UI.
    """

    def __init__(
        self,
        metadata: Metadata,
        info: ProjectInfo,
        settings: ProjectSettings,
        samples: IdentifiedCollection[Sample],
        song: Song,
    ) -> None:
        self.metadata: Metadata = metadata
        self.info: ProjectInfo = info
        self.settings: ProjectSettings = settings
        self.samples: IdentifiedCollection[Sample] = samples
        self.song: Song = song

    @classmethod
    def create(
        cls,
        *,
        title: str = DEFAULT_PROJECT_TITLE,
        author: str = DEFAULT_PROJECT_AUTHOR,
        comment: str = DEFAULT_PROJECT_COMMENT,
        rows_per_pattern: int = DEFAULT_ROWS_PER_PATTERN,
        settings: Optional[ProjectSettings] = None,
    ) -> Project:
        if settings is None:
            settings = ProjectSettings()

        info = ProjectInfo(
            title=title,
            author=author,
            comment=comment,
        )
        return cls(
            metadata=Metadata.default(),
            info=info,
            settings=settings,
            samples=IdentifiedCollection(),
            song=Song.empty(rows_per_pattern),
        )

    def sample(self, sample_id: str) -> Optional[Sample]:
        return self.samples.get(sample_id)

    def __repr__(self) -> str:
        return f"Project(title={self.info.title!r}, samples={len(self.samples)})"
