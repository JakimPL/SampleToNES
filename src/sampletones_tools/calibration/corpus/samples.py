from pathlib import Path
from typing import Final, List

import numpy as np

from sampletones_core.audio.io import read_recording
from sampletones_core.configs import Config
from sampletones_shared.logger import logger
from sampletones_tools.calibration.config.samples import SamplesConfig
from sampletones_tools.calibration.samples import is_fetched

from .families import Catalog, Family
from .item import CorpusItem

SAMPLES_CATEGORY: Final[str] = "samples"
SAMPLES_CATALOG: Final[Catalog] = [(Family.SAMPLES, SAMPLES_CATEGORY)]


def build_samples(config: Config, *, references: SamplesConfig, directory: Path) -> List[CorpusItem]:
    """The fetched recordings kept for listening, each cut to the window its reference names.

    A recording not fetched yet is left out, with a note on how to fetch it. A recording carries no
    truth, and is converted over the run's channels.

    Args:
        config: The configuration the run converts with, whose rate the recordings are read at.
        references: The recordings.
        directory: Where the fetched recordings are kept.

    Returns:
        List[CorpusItem]: One listed item per fetched recording, in the order the references list them.
    """
    items: List[CorpusItem] = []
    rate = config.library.sample_rate
    for reference in references.samples:
        if not is_fetched(reference, directory):
            logger.warning(f"{reference.name} is not fetched yet; `sampletones calibration --fetch-samples` fetches it")
            continue

        audio = read_recording(directory / reference.file_name, target_sample_rate=rate)
        window = audio[round(reference.start_seconds * rate) : round(reference.end_seconds * rate)]
        items.append(
            CorpusItem(
                name=reference.name,
                family=Family.SAMPLES,
                category=SAMPLES_CATEGORY,
                listed=True,
                audio=np.asarray(window, dtype=np.float32),
                truth=None,
                channels=None,
                stems=None,
            )
        )

    return items
