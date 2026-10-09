from __future__ import annotations

from typing import Optional

from sampletones_core.data import Metadata
from sampletones_core.project.voices.voice import VoiceUnion
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

    Owns the voices — samples embedding their own reconstruction, and shapes carrying
    their own envelopes — and the song arrangement. References inside the song point at
    voices by their stable ``id``; the :class:`IdentifiedCollection` resolves those ids
    in O(1) while also exposing reorder-safe positions for the UI.
    """

    def __init__(
        self,
        metadata: Metadata,
        info: ProjectInfo,
        settings: ProjectSettings,
        voices: IdentifiedCollection[VoiceUnion],
        song: Song,
    ) -> None:
        self.metadata: Metadata = metadata
        self.info: ProjectInfo = info
        self.settings: ProjectSettings = settings
        self.voices: IdentifiedCollection[VoiceUnion] = voices
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
            voices=IdentifiedCollection(),
            song=Song.empty(rows_per_pattern),
        )

    def voice(self, voice_id: str) -> Optional[VoiceUnion]:
        return self.voices.get(voice_id)

    def snapshot(self) -> Project:
        """An independent project holding the very values this one holds.

        The project is a tree of shells over values. A shell is changed in place by a gesture: the
        info, the settings, the voices list and each voice, the song with its order and its
        channels' pools. A value is never changed once made: the metadata, a sample's
        reconstruction, an instrument's envelopes, a pattern and its rows. The snapshot copies the
        shells and holds the values, so an edit of either project replaces a value in its own
        shell and leaves the other as it was, and a history entry owns only the values its
        gesture made.
        """
        return Project(
            metadata=self.metadata,
            info=self.info.model_copy(),
            settings=self.settings.model_copy(),
            voices=IdentifiedCollection(voice.snapshot() for voice in self.voices),
            song=self.song.snapshot(),
        )

    def __repr__(self) -> str:
        return f"Project(title={self.info.title!r}, voices={len(self.voices)})"
