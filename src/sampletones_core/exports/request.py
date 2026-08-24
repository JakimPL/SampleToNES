from __future__ import annotations

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
class InstrumentSource:
    """One instrument ready to be written, awaiting the name its destination gives it.

    An instrument reaches a file the same way whatever produced it — a channel of the open
    reconstruction, a channel of a project sample, or a voice written by hand — so each of those
    answers with this, and one path carries it the rest of the way. The name is left out because
    the destination states it: whoever saves the file names the instrument the file carries.

    Attributes:
        channel: The NES channel the envelopes are read for, which a backend sounding them on
            its own plays them through.
        features: The per-dimension envelopes describing the instrument.
        loop_point: The tick the instrument repeats from while its note is held, or ``None``
            where it plays its envelopes once.
        nes_frequency: Rate in Hz the envelopes advance at, one item per tick.
        tuning: Where concert pitch sits for the envelopes.
    """

    channel: ChannelName
    features: Features
    loop_point: Optional[int]
    nes_frequency: int
    tuning: Tuning

    def named(self, name: str) -> InstrumentExport:
        """The request a backend writes, under the name its destination gave it.

        Args:
            name: The name the written instrument carries.

        Returns:
            InstrumentExport: The instrument, ready for a backend.
        """
        return InstrumentExport(
            name=name,
            channel=self.channel,
            features=self.features,
            loop_point=self.loop_point,
            nes_frequency=self.nes_frequency,
            tuning=self.tuning,
        )


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
