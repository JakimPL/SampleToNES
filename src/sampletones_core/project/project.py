from __future__ import annotations

from typing import Optional

from sampletones_core.data import Metadata
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.structures import IndexedCollection
from sampletones_shared.constants.project import DEFAULT_PROJECT_AUTHOR, DEFAULT_PROJECT_COMMENT, DEFAULT_PROJECT_TITLE

from .info import ProjectInfo
from .settings import ProjectSettings
from .song import Song


class Project:
    """The top-level container for everything a user composes.

    Owns the instruments (each embedding its own reconstruction) and the song
    arrangement. References inside the song point at instruments by their stable
    ``id``; the :class:`IndexedCollection` provides reorder-safe positional and
    identity access for the UI.
    """

    def __init__(
        self,
        metadata: Metadata,
        info: ProjectInfo,
        settings: ProjectSettings,
        instruments: IndexedCollection[Instrument],
        song: Song,
    ) -> None:
        self.metadata: Metadata = metadata
        self.info: ProjectInfo = info
        self.settings: ProjectSettings = settings
        self.instruments: IndexedCollection[Instrument] = instruments
        self.song: Song = song

    @classmethod
    def create(
        cls,
        *,
        title: str = DEFAULT_PROJECT_TITLE,
        author: str = DEFAULT_PROJECT_AUTHOR,
        comment: str = DEFAULT_PROJECT_COMMENT,
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
            instruments=IndexedCollection(),
            song=Song.empty(settings.rows_per_pattern),
        )

    def instrument(self, instrument_id: str) -> Optional[Instrument]:
        for instrument in self.instruments:
            if instrument.id == instrument_id:
                return instrument

        return None

    def __repr__(self) -> str:
        return f"Project(title={self.info.title!r}, instruments={len(self.instruments)})"
