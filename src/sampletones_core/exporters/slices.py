from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterator, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.feature import Features
from sampletones_core.exporters.naming import instrument_slice_name
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.project import Project


@dataclass(frozen=True)
class InstrumentSlot:
    """Where a sample's channel slice landed in the instrument table."""

    index: int
    initial_pitch: int


InstrumentTable = Dict[Tuple[str, ChannelName], InstrumentSlot]


@dataclass(frozen=True)
class SampleSlice:
    """One channel slice of a project sample, numbered for the instrument table.

    Attributes:
        index: Position the slice takes in the exported instrument table.
        sample: The sample whose reconstruction the slice came from.
        channel: The NES channel the slice covers.
        features: The per-dimension envelopes describing the slice.
    """

    index: int
    sample: Sample
    channel: ChannelName
    features: Features

    @property
    def instrument_name(self) -> str:
        """The exported instrument's name, naming both its sample and its channel."""
        return instrument_slice_name(self.sample.name, self.channel)

    @property
    def key(self) -> Tuple[str, ChannelName]:
        """The identity a pattern row references the slice by."""
        return (self.sample.id, self.channel)

    @property
    def slot(self) -> InstrumentSlot:
        """The table position and reference pitch a pattern row resolves through."""
        return InstrumentSlot(
            index=self.index,
            initial_pitch=self.features.initial_pitch,
        )


def iterate_sample_slices(project: Project) -> Iterator[SampleSlice]:
    """Walks every channel slice of every sample in instrument-table order.

    A sample contributes one slice per channel that plays, so it yields one to four. Slices
    are numbered in sample order, then channel order, which fixes the instrument numbering
    every tracker format builds on. Each sample's features are exported once, so a caller
    reads a reconstruction's envelopes at a single cost.

    Args:
        project: The project whose samples are exported.

    Yields:
        SampleSlice: Each slice alongside the index it takes in the instrument table.
    """
    index = 0
    for sample in project.samples:
        features_by_channel = sample.reconstruction.export()
        for channel in ChannelName.items():
            features = features_by_channel[channel]
            if not features.has_frames:
                continue

            yield SampleSlice(
                index=index,
                sample=sample,
                channel=channel,
                features=features,
            )
            index += 1
