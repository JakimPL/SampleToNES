from pathlib import Path
from typing import List

from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.request import ProjectExport
from sampletones_player.builder import song_from_reconstruction
from sampletones_player.compression.scheme import CompressionScheme
from sampletones_player.driver.image import DriverImage
from sampletones_player.export.backends import program_backends
from sampletones_player.rom.file import rom_to_bytes
from sampletones_player.shell.image import ShellImage
from sampletones_player.shell.patterns import load_patterns
from sampletones_shared.paths.extensions import EXT_FILE_ROM
from sampletones_shared.utils.serialization import save_binary
from sampletones_tools.corpus.build import Corpus
from sampletones_tools.samples.nsf import SONG_NAME, exported_information


def write_samples(corpus: Corpus, output: Path) -> List[Path]:
    """Writes each corpus sample as a cartridge of its own, then the arrangement through the backend.

    Args:
        corpus: The samples and the arrangement.
        output: The directory the files are written into.

    Returns:
        List[Path]: The files written, the samples first and the arrangement last.
    """
    driver, shell, patterns = DriverImage.load(), ShellImage.load(), load_patterns()
    written: List[Path] = []
    for name, sample in corpus.catalog.items():
        destination = output / f"{name}{EXT_FILE_ROM}"
        song = song_from_reconstruction(sample.reconstruction, loop_tick=None, scheme=CompressionScheme.SEARCH)
        information = exported_information(name, corpus.project.info.author)
        save_binary(destination, rom_to_bytes(song, information, driver, shell, patterns))
        written.append(destination)

    arrangement = output / f"{SONG_NAME}{EXT_FILE_ROM}"
    program_backends()[ExportFormat.ROM].write_project(arrangement, ProjectExport(project=corpus.project))
    written.append(arrangement)
    return written
