from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterator, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.feature import Features
from sampletones_core.exporters.naming import instrument_slice_name
from sampletones_core.project.project import Project
from sampletones_core.project.voices.sample import Sample


@dataclass(frozen=True)
class InstrumentSlot:
    """Where a voice's channel slice landed in the instrument table."""

    index: int
    initial_pitch: int


InstrumentTable = Dict[Tuple[str, ChannelName], InstrumentSlot]


@dataclass(frozen=True)
class VoiceSlice:
    """One channel slice of a project voice, numbered for the instrument table.

    Attributes:
        index: Position the slice takes in the exported instrument table.
        voice: The voice the slice came from.
        channel: The NES channel the slice covers.
        features: The per-dimension envelopes describing the slice.
    """

    index: int
    voice: Sample
    channel: ChannelName
    features: Features

    @property
    def instrument_name(self) -> str:
        """The exported instrument's name, naming both its sample and its channel."""
        return instrument_slice_name(self.voice.name, self.channel)

    @property
    def key(self) -> Tuple[str, ChannelName]:
        """The identity a pattern row references the slice by."""
        return (self.voice.id, self.channel)

    @property
    def slot(self) -> InstrumentSlot:
        """The table position and reference pitch a pattern row resolves through."""
        return InstrumentSlot(
            index=self.index,
            initial_pitch=self.features.initial_pitch,
        )


def iterate_voice_slices(project: Project) -> Iterator[VoiceSlice]:
    """Walks every channel slice of every voice in instrument-table order.

    A voice contributes one slice per channel that plays, so a sample yields one to four. Slices
    are numbered in voice order, then channel order, which fixes the instrument numbering every
    tracker format builds on. Each voice's features are exported once, so a caller reads a
    reconstruction's envelopes at a single cost.

    Args:
        project: The project whose voices are exported.

    Yields:
        VoiceSlice: Each slice alongside the index it takes in the instrument table.
    """
    index = 0
    for voice in project.voices:
        features_by_channel = voice.reconstruction.export()
        for channel in ChannelName.items():
            features = features_by_channel[channel]
            if not features.has_frames:
                continue

            yield VoiceSlice(
                index=index,
                voice=voice,
                channel=channel,
                features=features,
            )
            index += 1
