from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Tuple

from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.song import SongPlanes


class SongGroup(StrEnum):
    """Which kind of song a corpus entry is, which is what the report aggregates over.

    Attributes:
        PROJECT: A project as it stands on disk, a few seconds of patterns.
        LONG_PROJECT: A project with its order repeated to the length an export is measured at.
        RECONSTRUCTION: A stem reconstructed from audio, its planes turning over at nearly
            every tick.
    """

    PROJECT = "project"
    LONG_PROJECT = "project-long"
    RECONSTRUCTION = "reconstruction"


@dataclass(frozen=True)
class StudySong:
    """One song the study measures the codec on.

    Attributes:
        name: What the song is called in a report.
        group: Which kind of song it is.
        source: The file the song was read from.
        planes: The planes the codec compresses.
        seeds: The phrases the song's instruments offer the dictionary.
        pitches: The timer each pitch of the song sounds at.
    """

    name: str
    group: SongGroup
    source: Path
    planes: SongPlanes
    seeds: Tuple[Phrase, ...]
    pitches: PitchTable

    @property
    def ticks(self) -> int:
        """The ticks the song lasts."""
        return self.planes.ticks
