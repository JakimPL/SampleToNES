from dataclasses import dataclass
from pathlib import Path

from sampletones_core.reconstructions.converter.paths.fields import (
    ConfigDirectoryFields,
)


@dataclass(frozen=True)
class SampleVariant:
    """One reconstruction of a source audio, with the configuration that produced it."""

    config: ConfigDirectoryFields
    path: Path
