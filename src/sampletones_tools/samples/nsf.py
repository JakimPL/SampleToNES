from pathlib import Path
from typing import Final, List

from sampletones_core.exports.request import ProjectExport
from sampletones_player.builder import song_from_reconstruction
from sampletones_player.driver.image import DriverImage
from sampletones_player.export import NSFBackend
from sampletones_player.nsf.file import write_nsf
from sampletones_player.nsf.information import NSFInformation
from sampletones_shared.paths.extensions import EXT_FILE_NSF
from sampletones_tools.corpus.build import Corpus

ARTIST: Final[str] = "Integration"
SONG_NAME: Final[str] = "song"


def exported_information(name: str) -> NSFInformation:
    """The header text an exported sample carries."""
    return NSFInformation(title=name, artist=ARTIST)


def write_samples(corpus: Corpus, output: Path) -> List[Path]:
    """Writes each corpus sample as a program of its own, then the arrangement through the backend.

    Args:
        corpus: The samples and the arrangement.
        output: The directory the files are written into.

    Returns:
        List[Path]: The files written, the samples first and the arrangement last.
    """
    image = DriverImage.load()
    written: List[Path] = []
    for name, sample in corpus.catalog.items():
        destination = output / f"{name}{EXT_FILE_NSF}"
        write_nsf(
            destination,
            song_from_reconstruction(sample.reconstruction, loop_tick=None),
            exported_information(name),
            image,
        )
        written.append(destination)

    arrangement = output / f"{SONG_NAME}{EXT_FILE_NSF}"
    NSFBackend().write_project(
        arrangement,
        ProjectExport(project=corpus.project),
    )
    written.append(arrangement)
    return written
