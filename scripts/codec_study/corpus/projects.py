from math import ceil
from pathlib import Path

from codec_study.corpus.song import SongGroup, StudySong
from sampletones_core.performance import song_instructions
from sampletones_core.project.container import ProjectContainer
from sampletones_core.project.project import Project
from sampletones_core.project.tuning import tuning_from_project
from sampletones_core.timers.utils import get_timer_table
from sampletones_core.timing import SongTiming
from sampletones_player.builder import streams_from_instructions
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.separate import planes_from_streams
from sampletones_player.compression.seeds import phrases_from_project
from sampletones_shared.utils.progress import silent_reporter


def project_song(path: Path) -> StudySong:
    """Reads a project file as the song its arrangement plays.

    Args:
        path: The project file.

    Returns:
        StudySong: The song, seeded with the phrases the project's instruments offer.
    """
    return _song(path.stem, SongGroup.PROJECT, path, ProjectContainer.load(path))


def lengthened_song(
    path: Path,
    seconds: int,
) -> StudySong:
    """Reads a project file as its arrangement repeated until the song lasts ``seconds``.

    A project on disk is a few seconds of patterns, and an export is measured against a song of
    minutes, so the whole order is played through as many times as that takes.

    Args:
        path: The project file.
        seconds: How long the song is to last.

    Returns:
        StudySong: The song, seeded with the phrases the project's instruments offer.
    """
    project = ProjectContainer.load(path)
    return _song(
        f"{path.stem} ({seconds} s)",
        SongGroup.LONG_PROJECT,
        path,
        _repeated(project, seconds),
    )


def _song(
    name: str,
    group: SongGroup,
    source: Path,
    project: Project,
) -> StudySong:
    tuning = tuning_from_project(project)
    pitches = PitchTable.from_tuning(tuning)
    streams = streams_from_instructions(
        song_instructions(project, silent_reporter),
        get_timer_table(tuning),
    )
    return StudySong(
        name=name,
        group=group,
        source=source,
        planes=planes_from_streams(streams, pitches),
        seeds=phrases_from_project(project, tuning),
        pitches=pitches,
    )


def _repeated(
    project: Project,
    seconds: int,
) -> Project:
    groove = SongTiming.from_project(project).groove()
    repetitions = max(1, ceil(seconds * project.settings.nes_frequency / groove.total_ticks))
    longer = Project.create(
        rows_per_pattern=project.song.rows_per_pattern,
        settings=project.settings,
    )
    for voice in project.voices:
        longer.voices.append(voice)

    longer.song = project.song.model_copy(deep=True)
    for _ in range(repetitions - 1):
        longer.song.order.extend(dict(frame) for frame in project.song.order)

    return longer
