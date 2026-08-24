from dataclasses import dataclass
from typing import Optional, Tuple

from sampletones_application.constants.instruments import INSTRUMENT_CHANNEL
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.slices import (
    FIRST_INSTRUMENT_INDEX,
    InstrumentEntry,
    voice_instrument_entries,
)
from sampletones_core.exports.request import InstrumentSource
from sampletones_core.project.project import Project
from sampletones_core.project.tuning import tuning_from_project
from sampletones_core.project.voices.voice import VoiceUnion


@dataclass(frozen=True)
class ExportableInstrument:
    """One instrument ready to be asked for a destination.

    Attributes:
        name: The name the save dialog suggests, which the written instrument keeps unless the
            reader renames the file.
        source: The instrument itself, awaiting the name its destination gives it.
    """

    name: str
    source: InstrumentSource


def voice_entries(voice: VoiceUnion) -> Tuple[InstrumentEntry, ...]:
    """The instruments one voice offers to an export.

    A module writing every voice and a file writing one read the same rule, so a reader is offered
    exactly the instruments a module would have held: a sample yields one per channel its
    reconstruction found frames for, and a voice written by hand yields the single set of envelopes
    every channel reads.

    Args:
        voice: The voice whose instruments are offered.

    Returns:
        Tuple[InstrumentEntry, ...]: Its instruments, in channel order.
    """
    return tuple(
        voice_instrument_entries(voice, start_index=FIRST_INSTRUMENT_INDEX),
    )


def sounding_channel(entry: InstrumentEntry) -> ChannelName:
    """The channel a file holding one instrument alone sounds it on.

    A sample's slice states the channel it was reconstructed for, and that is the channel it is
    sounded on. A voice written by hand states one set of envelopes for no channel in particular,
    and a file must still play it somewhere, so it is sounded where the app reads it: the channel
    its own editor shows it under, whose reference is the tonal root its envelopes are measured
    against.

    Args:
        entry: The instrument being written.

    Returns:
        ChannelName: The channel the written file plays the instrument through.
    """
    if entry.channel is None:
        return INSTRUMENT_CHANNEL

    return entry.channel


def instrument_source(
    project: Project,
    entry: InstrumentEntry,
) -> InstrumentSource:
    """One of a voice's instruments, measured at the rate and tuning its project plays it at.

    Args:
        project: The project the voice belongs to, which states the rate and the tuning.
        entry: The instrument being written.

    Returns:
        InstrumentSource: The instrument, awaiting the name its destination gives it.

    Raises:
        ValueError: If the project's samples were reconstructed against tunings that differ.
    """
    return InstrumentSource(
        channel=sounding_channel(entry),
        features=entry.features,
        loop_point=entry.loop_point,
        nes_frequency=project.settings.nes_frequency,
        tuning=tuning_from_project(project),
    )


def exportable_instrument(
    project: Project,
    entry: InstrumentEntry,
) -> ExportableInstrument:
    """One of a voice's instruments, ready to be given a destination.

    Args:
        project: The project the voice belongs to, which states the rate and the tuning.
        entry: The instrument being written.

    Returns:
        ExportableInstrument: The instrument and the name to suggest for it.

    Raises:
        ValueError: If the project's samples were reconstructed against tunings that differ.
    """
    return ExportableInstrument(
        name=entry.name,
        source=instrument_source(project, entry),
    )


def voice_instrument_channels(
    project: Project,
    voice_id: str,
) -> Tuple[Optional[ChannelName], ...]:
    """What one project voice offers to an export, each named by the channel it is stated for.

    A sample answers with the channels its reconstruction found frames for; a voice written by hand
    answers with a single ``None``, since its one set of envelopes belongs to no channel in
    particular.

    Args:
        project: The project the voice belongs to.
        voice_id: The voice whose instruments are offered.

    Returns:
        Tuple[Optional[ChannelName], ...]: One entry per instrument the voice holds, empty while
        the pool holds no such voice or the voice writes nothing.
    """
    voice = project.voices.get(voice_id)
    if voice is None:
        return ()

    return tuple(entry.channel for entry in voice_entries(voice))


def voice_instrument(
    project: Project,
    voice_id: str,
    channel_name: Optional[ChannelName],
) -> Optional[ExportableInstrument]:
    """One of a project voice's instruments, named by the channel it is stated for.

    Args:
        project: The project the voice belongs to.
        voice_id: The voice the instrument belongs to.
        channel_name: The channel the instrument is stated for, ``None`` where the voice holds the
            one set of envelopes every channel reads.

    Returns:
        Optional[ExportableInstrument]: The instrument and the name to suggest for it, or ``None``
        where the pool holds no such voice or the voice holds no instrument answering to that
        channel.

    Raises:
        ValueError: If the project's samples were reconstructed against tunings that differ.
    """
    voice = project.voices.get(voice_id)
    if voice is None:
        return None

    entry = next(
        (candidate for candidate in voice_entries(voice) if candidate.channel == channel_name),
        None,
    )
    if entry is None:
        return None

    return exportable_instrument(project, entry)
