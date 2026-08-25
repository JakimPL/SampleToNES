from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig


@dataclass(frozen=True)
class ConversionJob:
    """One reconstruction to build, and everything needed to build it.

    A job carries the recordings that are mixed into the target, the stems setup that hands
    their channels out, and the file the result is written to. It is the unit a conversion
    is divided into: a classic conversion is one job over one source, a stems conversion one
    job over several, and a batch as many single-source jobs as the directory holds.
    """

    sources: Tuple[Path, ...]
    stems: StemsConfig
    output_path: Path
