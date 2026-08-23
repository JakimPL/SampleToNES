from dataclasses import dataclass
from typing import Optional, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.feature import Features
from sampletones_core.project.project import Project
from sampletones_shared.music import Tuning


@dataclass(frozen=True)
class InstrumentExport:
    """One channel slice of a reconstruction, ready for a backend to write.

    Attributes:
        name: Name the written instrument carries.
        channel: The NES channel the slice was reconstructed for.
        features: The per-dimension envelopes describing the slice.
        loop_point: The tick the instrument repeats from while its note is held, or ``None``
            where it plays its envelopes once.
        nes_frequency: Rate in Hz the envelopes advance at, one item per tick.
        tuning: Where concert pitch sat for the reconstruction the slice came from.
    """

    name: str
    channel: ChannelName
    features: Features
    loop_point: Optional[int]
    nes_frequency: int
    tuning: Tuning


@dataclass(frozen=True)
class SampleExport:
    """Every channel slice of one reconstruction.

    Attributes:
        name: Name of the reconstruction the slices came from.
        instruments: One entry per channel the reconstruction covers.
        nes_frequency: Rate in Hz the envelopes advance at, one item per tick.
        tuning: Where concert pitch sat for the reconstruction the slices came from.
    """

    name: str
    instruments: Tuple[InstrumentExport, ...]
    nes_frequency: int
    tuning: Tuning


@dataclass(frozen=True)
class ProjectExport:
    """A whole composition — its samples and the song that arranges them.

    Attributes:
        project: The project to write.
    """

    project: Project
