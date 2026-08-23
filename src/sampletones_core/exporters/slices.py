from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterator, Optional, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.feature import Features
from sampletones_core.exporters.naming import instrument_slice_name
from sampletones_core.project.project import Project
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.shape import Shape
from sampletones_core.project.voices.voice import VoiceUnion, voice_channels


@dataclass(frozen=True)
class InstrumentSlot:
    """Where a row naming a voice on one channel lands: the instrument it plays and its reference."""

    index: int
    initial_pitch: int


InstrumentTable = Dict[Tuple[str, ChannelName], InstrumentSlot]


@dataclass(frozen=True)
class VoiceSlice:
    """What one channel of one voice plays, in the envelope terms every backend reads.

    Attributes:
        voice: The voice the slice came from.
        channel: The NES channel the slice covers.
        features: The per-dimension envelopes describing the slice.
    """

    voice: VoiceUnion
    channel: ChannelName
    features: Features

    @property
    def instrument_name(self) -> str:
        """The exported instrument's name, naming both its voice and its channel."""
        return instrument_slice_name(self.voice.name, self.channel)

    @property
    def key(self) -> Tuple[str, ChannelName]:
        """The identity a pattern row references the slice by."""
        return (self.voice.id, self.channel)


@dataclass(frozen=True)
class InstrumentEntry:
    """One instrument an export writes, and the channels whose rows reach it.

    A sample's channels each carry frames of their own, so each becomes an instrument answering
    for that channel alone. A shape carries one set of envelopes every channel reads, so it
    becomes one instrument answering for every channel it sounds on, each against its own root —
    which is the instrument model FamiTracker itself uses.

    Attributes:
        index: Position the instrument takes in the exported table.
        voice_id: The voice a row names to reach it.
        name: The name the tracker lists it by.
        features: The envelopes written into it.
        loop_point: The tick its envelopes repeat from, or ``None`` where they play once.
        slots: Per channel it answers for, the table position and the reference that channel reads.
    """

    index: int
    voice_id: str
    name: str
    features: Features
    loop_point: Optional[int]
    slots: Dict[ChannelName, InstrumentSlot]


def iterate_voice_slices(project: Project) -> Iterator[VoiceSlice]:
    """Walks what every channel of every voice plays, in voice order then channel order.

    A voice contributes one slice per channel it sounds on, so a sample yields one to four and a
    shape yields one per channel its envelopes make a frame for. Each voice is read once, so a
    caller reads a reconstruction's envelopes at a single cost.

    Args:
        project: The project whose voices are exported.

    Yields:
        VoiceSlice: What each channel of each voice plays.
    """
    for voice in project.voices:
        match voice:
            case Sample():
                features_by_channel = voice.reconstruction.export()
                for channel in ChannelName.items():
                    features = features_by_channel[channel]
                    if features.has_frames:
                        yield VoiceSlice(voice=voice, channel=channel, features=features)
            case Shape():
                for channel in voice_channels(voice):
                    yield VoiceSlice(voice=voice, channel=channel, features=voice.features(channel))


def iterate_instrument_entries(project: Project) -> Iterator[InstrumentEntry]:
    """Walks the instruments an export writes, numbered in voice order then channel order.

    Args:
        project: The project whose voices are exported.

    Yields:
        InstrumentEntry: Each instrument alongside the channels whose rows reach it.
    """
    index = 0
    for voice in project.voices:
        match voice:
            case Sample():
                features_by_channel = voice.reconstruction.export()
                for channel in ChannelName.items():
                    features = features_by_channel[channel]
                    if not features.has_frames:
                        continue

                    yield InstrumentEntry(
                        index=index,
                        voice_id=voice.id,
                        name=instrument_slice_name(voice.name, channel),
                        features=features,
                        loop_point=voice.loop_point,
                        slots={channel: InstrumentSlot(index=index, initial_pitch=features.initial_pitch)},
                    )
                    index += 1
            case Shape():
                channels = voice_channels(voice)
                if not channels:
                    continue

                yield InstrumentEntry(
                    index=index,
                    voice_id=voice.id,
                    name=voice.name,
                    features=voice.instrument_features(),
                    loop_point=voice.loop_point,
                    slots={
                        channel: InstrumentSlot(index=index, initial_pitch=voice.reference(channel))
                        for channel in channels
                    },
                )
                index += 1
