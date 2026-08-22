from dataclasses import dataclass
from math import ceil
from typing import Dict, Final, List, Tuple

from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.timing import SongTiming
from sampletones_player.builder import song_from_project, song_from_reconstruction
from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.separate import planes_from_streams
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.compression.seeds import phrases_from_project
from sampletones_player.song import Song
from sampletones_shared.music import Tuning
from tests.integration.nsf.songs import RECORD_BYTES_PER_TICK, lengthened

ARRANGEMENT: Final[str] = "arrangement"
LONG_ARRANGEMENT: Final[str] = "arrangement, three minutes"
TARGET_SECONDS: Final[int] = 180


@dataclass(frozen=True)
class CorpusEntry:
    """One song the codec is measured on, alongside the phrases its own instruments offer."""

    name: str
    song: Song
    seeds: Tuple[Phrase, ...]
    tuning: Tuning

    @property
    def pitches(self) -> PitchTable:
        """The timer each pitch of the song sounds at."""
        return PitchTable.from_tuning(self.tuning)

    @property
    def planes(self) -> SongPlanes:
        """The eight planes the song separates into."""
        return planes_from_streams(self.song.streams, self.pitches)

    @property
    def records(self) -> int:
        """The bytes the song takes as one record per tick per channel."""
        return RECORD_BYTES_PER_TICK * self.song.ticks


def _sample_project(
    sample: Sample,
    settings: ProjectSettings,
) -> Project:
    project = Project.create(settings=settings)
    project.samples.append(sample)
    return project


def sample_entries(
    instrument_catalog: Dict[str, Sample],
    settings: ProjectSettings,
) -> Tuple[CorpusEntry, ...]:
    """Each catalog sample as a song of its own, played at the tuning it was reconstructed at.

    Args:
        instrument_catalog: The samples the integration suite reads.
        settings: The project settings a sample is seeded under.

    Returns:
        Tuple[CorpusEntry, ...]: One entry per sample, in catalog order.
    """
    entries: List[CorpusEntry] = []
    for name, sample in instrument_catalog.items():
        tuning = sample.reconstruction.config.library.tuning
        entries.append(
            CorpusEntry(
                name=name,
                song=song_from_reconstruction(sample.reconstruction, loop_tick=None),
                seeds=phrases_from_project(_sample_project(sample, settings), tuning),
                tuning=tuning,
            )
        )

    return tuple(entries)


def arrangement_entry(
    name: str,
    project: Project,
) -> CorpusEntry:
    """A whole project flattened into one song, at concert tuning.

    Args:
        name: What the entry is called in a report.
        project: The arrangement the song is walked from.

    Returns:
        CorpusEntry: The song and the phrases the project's instruments offer.
    """
    tuning = Tuning()
    return CorpusEntry(
        name=name,
        song=song_from_project(project, tuning, loop_tick=None),
        seeds=phrases_from_project(project, tuning),
        tuning=tuning,
    )


def lengthened_arrangement(
    project: Project,
    seconds: int,
) -> Project:
    """``project`` with its order repeated until the song lasts ``seconds``.

    The corpus arrangement is a couple of seconds long, and what the program area is measured
    against is a song of minutes, so the order is played through as many times as that takes.

    Args:
        project: The arrangement to repeat.
        seconds: How long the song is to last.

    Returns:
        Project: A copy of the project, its order repeated.
    """
    groove = SongTiming.from_project(project).groove()
    frames = ceil(seconds * project.settings.nes_frequency / groove.total_ticks)
    return lengthened(project, frames)


def build_corpus(
    instrument_catalog: Dict[str, Sample],
    integration_project: Project,
) -> Tuple[CorpusEntry, ...]:
    """The songs the codec is measured on: each sample alone, and the arrangement at two lengths.

    Args:
        instrument_catalog: The samples the integration suite reads.
        integration_project: The arrangement those samples are played in.

    Returns:
        Tuple[CorpusEntry, ...]: The samples first, then the arrangement, then the long one.
    """
    return (
        *sample_entries(instrument_catalog, integration_project.settings),
        arrangement_entry(ARRANGEMENT, integration_project),
        arrangement_entry(LONG_ARRANGEMENT, lengthened_arrangement(integration_project, TARGET_SECONDS)),
    )
