from pathlib import Path
from typing import NamedTuple, Optional, Self, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sampletones_core.constants.enums import AudioSourceType
from sampletones_shared.utils.serialization import load_yaml_model


class Listening(NamedTuple):
    """What the Reconstructions tab sounds: the Source card's choice and the names of the stem rows ticked."""

    source: AudioSourceType
    stems: Tuple[str, ...]


class Segment(BaseModel):
    """One stretch of the footage under one listening, from the song time it begins at."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    start: float = Field(alias="from", ge=0.0)
    audio: AudioSourceType
    stems: Tuple[str, ...] = Field(min_length=1)

    @property
    def listening(self) -> Listening:
        return Listening(source=self.audio, stems=tuple(sorted(self.stems)))


class Timeline(BaseModel):
    """The footage as listenings over the song, in seconds of the document's audio."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    start: float = Field(ge=0.0)
    end: float
    segments: Tuple[Segment, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_order(self) -> Self:
        """Raises:
        ValueError: If the first segment begins elsewhere than the start, the segments begin out of order,
            or the footage ends before its last segment begins.
        """
        starts = [segment.start for segment in self.segments]
        if starts[0] != self.start:
            raise ValueError("The first segment must begin at the timeline's start")

        if any(later <= earlier for earlier, later in zip(starts, starts[1:])):
            raise ValueError("Segments must begin in increasing order")

        if self.end <= starts[-1]:
            raise ValueError("The timeline must end after its last segment begins")

        return self


class Footage(BaseModel):
    """What one piece of footage films: the document opened on the Reconstructions tab, the frame rate it is
    filmed at, and the timeline of listenings it walks through.

    Attributes:
        document: The reconstruction filmed, relative to the specification's folder, or the demo tree's piece
            where absent.
        frame_rate: Frames a second of footage holds; the document's NES frequency must be a multiple of it.
        timeline: The listenings over the song.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    document: Optional[Path]
    frame_rate: int = Field(gt=0)
    timeline: Timeline

    @classmethod
    def load(cls, path: Path) -> Self:
        return load_yaml_model(path, cls)
