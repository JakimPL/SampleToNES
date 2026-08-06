from dataclasses import dataclass
from typing import Tuple

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.exporters.feature import Features
from sampletones_core.project.project import Project


@dataclass(frozen=True)
class InstrumentExport:
    """One generator slice of a reconstruction, ready for a backend to write.

    Attributes:
        name: Name the written instrument carries.
        generator: The NES channel the slice was reconstructed for.
        features: The per-dimension envelopes describing the slice.
        loop: Whether the instrument repeats its envelopes while its note is held.
        nes_frequency: Rate in Hz the envelopes advance at, one item per tick.
    """

    name: str
    generator: GeneratorName
    features: Features
    loop: bool
    nes_frequency: int


@dataclass(frozen=True)
class SampleExport:
    """Every generator slice of one reconstruction.

    Attributes:
        name: Name of the reconstruction the slices came from.
        instruments: One entry per channel the reconstruction covers.
        nes_frequency: Rate in Hz the envelopes advance at, one item per tick.
    """

    name: str
    instruments: Tuple[InstrumentExport, ...]
    nes_frequency: int


@dataclass(frozen=True)
class ProjectExport:
    """A whole composition — its samples and the song that arranges them.

    Attributes:
        project: The project to write.
    """

    project: Project
