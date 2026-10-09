from pathlib import Path
from typing import Final, List

from sampletones_core.formats.famitracker.export import write_ftm
from sampletones_tools.corpus.build import Corpus

MODULE_FILENAME: Final[str] = "drums.ftm"


def write_samples(corpus: Corpus, output: Path) -> List[Path]:
    """Writes the corpus arrangement as one FamiTracker module.

    Args:
        corpus: The samples and the arrangement.
        output: The directory the module is written into.

    Returns:
        List[Path]: The module written.
    """
    destination = output / MODULE_FILENAME
    write_ftm(destination, corpus.project)
    return [destination]
