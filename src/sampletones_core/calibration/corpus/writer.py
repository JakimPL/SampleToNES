from pathlib import Path
from typing import Dict, List

from sampletones_core.audio.io import write_wave
from sampletones_shared.paths.extensions import EXT_FILE_WAVE
from sampletones_shared.utils.system.paths import get_filename

from .item import CorpusItem


def write_corpus(
    items: List[CorpusItem],
    directory: Path,
    sample_rate: int,
) -> Dict[str, Path]:
    """
    Write every corpus item as a WAV file.

    Args:
        items: Corpus items to write.
        directory: Target directory, created when absent.
        sample_rate: Sampling rate of the items in Hz.

    Returns:
        The written file path per item name.
    """
    directory.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, Path] = {}
    for item in items:
        path = directory / get_filename(item.name, EXT_FILE_WAVE)
        write_wave(path, sample_rate, item.audio)
        paths[item.name] = path

    return paths
