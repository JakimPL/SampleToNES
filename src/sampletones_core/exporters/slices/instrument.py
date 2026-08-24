from dataclasses import dataclass
from typing import Dict, Final, Iterator, Optional, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.feature import Features
from sampletones_core.exporters.naming import instrument_slice_name
from sampletones_core.project.project import Project
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceUnion, voice_channels

FIRST_INSTRUMENT_INDEX: Final[int] = 0


@dataclass(frozen=True)
class InstrumentSlot:
    """Where a row naming a voice on one channel lands: the instrument it plays and its reference."""

    index: int
    initial_pitch: int


InstrumentTable = Dict[Tuple[str, ChannelName], InstrumentSlot]


@dataclass(frozen=True)
class InstrumentEntry:
    """One instrument an export writes, and the channels whose rows reach it.

    A sample's channels each carry frames of their own, so each becomes an instrument answering
    for that channel alone. An instrument carries one set of envelopes every channel reads, so it
    becomes one instrument answering for every channel it sounds on, each against its own root —
    which is the instrument model FamiTracker itself uses.

    Attributes:
        index: Position the instrument takes in the exported table.
        voice_id: The voice a row names to reach it.
        name: The name the tracker lists it by.
        features: The envelopes written into it.
        channel: The channel ``features`` are stated for, or ``None`` where they are the one set
            every channel reads and belong to no channel in particular.
        slots: Per channel it answers for, the table position and the reference that channel reads.
    """

    index: int
    voice_id: str
    name: str
    features: Features
    channel: Optional[ChannelName]
    slots: Dict[ChannelName, InstrumentSlot]


def sample_instrument_entries(
    sample: Sample,
    *,
    start_index: int,
) -> Iterator[InstrumentEntry]:
    """The instruments a recording contributes: one per channel its conversion found frames for.

    Each carries the frames of one channel alone, so it is named after that channel and answers
    for it by itself.

    Args:
        sample: The sample being exported.
        start_index: The slot the first of its instruments is numbered under.

    Yields:
        InstrumentEntry: One instrument per playing channel.
    """
    features_by_channel = sample.reconstruction.export()
    index = start_index
    for channel in ChannelName.items():
        features = features_by_channel[channel]
        if not features.has_frames:
            continue

        yield InstrumentEntry(
            index=index,
            voice_id=sample.id,
            name=instrument_slice_name(sample.name, channel),
            features=features.repeating_from(sample.loop_point),
            channel=channel,
            slots={
                channel: InstrumentSlot(
                    index=index,
                    initial_pitch=features.initial_pitch,
                ),
            },
        )
        index += 1


def instrument_entries(
    instrument: Instrument,
    *,
    start_index: int,
) -> Iterator[InstrumentEntry]:
    """The instrument a hand-written voice contributes, which is its one envelope set.

    Every channel it sounds on reaches that set, each against the root it reads, so the entry
    answers for all of them and states its envelopes for none of them in particular.

    Args:
        instrument: The voice being exported.
        start_index: The slot the instrument is numbered under.

    Yields:
        InstrumentEntry: The one instrument, where its envelopes make a frame anywhere.
    """
    channels = voice_channels(instrument)
    if not channels:
        return

    yield InstrumentEntry(
        index=start_index,
        voice_id=instrument.id,
        name=instrument.name,
        features=instrument.instrument_features(),
        channel=None,
        slots={
            channel: InstrumentSlot(
                index=start_index,
                initial_pitch=instrument.reference(channel),
            )
            for channel in channels
        },
    )


def voice_instrument_entries(
    voice: VoiceUnion,
    *,
    start_index: int,
) -> Iterator[InstrumentEntry]:
    """The instruments an export writes for one voice, numbered from ``start_index``.

    This is the whole rule for what a voice contributes to an export, so a module writing every
    voice and a file writing one read the same thing: a reader is offered exactly the instruments
    a module would have held.

    Args:
        voice: The voice being exported.
        start_index: The slot the first of its instruments is numbered under.

    Yields:
        InstrumentEntry: Each instrument alongside the channels whose rows reach it.
    """
    match voice:
        case Sample():
            yield from sample_instrument_entries(voice, start_index=start_index)
        case Instrument():
            yield from instrument_entries(voice, start_index=start_index)


def iterate_instrument_entries(project: Project) -> Iterator[InstrumentEntry]:
    """Walks the instruments an export writes, numbered in voice order then channel order.

    Args:
        project: The project whose voices are exported.

    Yields:
        InstrumentEntry: Each instrument alongside the channels whose rows reach it.
    """
    index = FIRST_INSTRUMENT_INDEX
    for voice in project.voices:
        for entry in voice_instrument_entries(voice, start_index=index):
            yield entry
            index += 1
