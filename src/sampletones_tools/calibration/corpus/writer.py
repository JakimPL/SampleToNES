from pathlib import Path
from typing import Dict, Final, List, Tuple

import numpy as np

from sampletones_core.audio import write_wave
from sampletones_shared.paths.extensions import EXT_FILE_WAVE
from sampletones_shared.utils.system.paths import get_filename

from .item import CorpusItem

STEM_SUFFIX: Final[str] = "-stem"


def write_corpus(
    items: List[CorpusItem],
    directory: Path,
    sample_rate: int,
) -> Dict[str, Tuple[Path, ...]]:
    """
    Write every corpus item as WAV files: one for a sound converted as one recording, one per stem
    for a sound held as stems.

    Args:
        items: Corpus items to write.
        directory: Target directory, created when absent.
        sample_rate: Sampling rate of the items in Hz.

    Returns:
        The written file paths per item name, in the order the conversion reads them.
    """
    directory.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, Tuple[Path, ...]] = {}
    for item in items:
        written: List[Path] = []
        for name, audio in _recordings(item):
            path = directory / get_filename(name, EXT_FILE_WAVE)
            write_wave(path, sample_rate, audio)
            written.append(path)

        paths[item.name] = tuple(written)

    return paths


def _recordings(item: CorpusItem) -> List[Tuple[str, np.ndarray]]:
    """What a conversion of ``item`` reads, each beside the name it is written under: its stems, or its audio."""
    if item.stems is None:
        return [(item.name, item.audio)]

    return [(f"{item.name}{STEM_SUFFIX}{index}", source) for index, source in enumerate(item.stems.sources)]
