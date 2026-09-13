from pathlib import Path
from typing import Final, Tuple

from sampletones_core.reconstructions import Reconstruction
from sampletones_core.timers.utils import get_timer_table
from sampletones_player.builder import streams_from_instructions
from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.separate import planes_from_streams
from sampletones_tools.codec.study.corpus.song import SongGroup, StudySong

STEM_SUFFIX: Final[str] = ".stn"
NO_SEEDS: Final[Tuple[Phrase, ...]] = ()


def reconstruction_paths(path: Path) -> Tuple[Path, ...]:
    """The stem files ``path`` names: the file itself, or every stem under a directory.

    Args:
        path: A stem file or a directory holding stems.

    Returns:
        Tuple[Path, ...]: The stem files, a directory's in sorted order.
    """
    if path.is_dir():
        return tuple(sorted(path.rglob(f"*{STEM_SUFFIX}")))

    return (path,)


def reconstruction_song(
    name: str,
    path: Path,
) -> StudySong:
    """Reads a stem file as the song the console plays it as.

    A reconstruction sounds each of its slices once, so the song offers the dictionary nothing
    and the search fills it from what the streams themselves repeat.

    Args:
        name: What the song is called in a report.
        path: The stem file.

    Returns:
        StudySong: The song, at the tuning and rate the stem was reconstructed at.
    """
    reconstruction = Reconstruction.load(path)
    tuning = reconstruction.config.tuning
    pitches = PitchTable.from_tuning(tuning)
    streams = streams_from_instructions(
        reconstruction.instructions,
        get_timer_table(tuning),
    )
    return StudySong(
        name=name,
        group=SongGroup.RECONSTRUCTION,
        source=path,
        planes=planes_from_streams(streams, pitches),
        seeds=NO_SEEDS,
        pitches=pitches,
    )
