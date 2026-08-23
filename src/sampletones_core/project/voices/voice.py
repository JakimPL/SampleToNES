from typing import Iterable, Iterator, Tuple, Union

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.shape import Shape

VoiceUnion = Union[Sample, Shape]


def samples(voices: Iterable[VoiceUnion]) -> Iterator[Sample]:
    """The samples among a project's voices — those a reconstruction stands behind.

    Work that reads recorded audio — retuning, rendering a waveform, opening a document in the
    Reconstructions tab — concerns those alone, so it walks them rather than every voice.

    Args:
        voices: The project's voices.

    Yields:
        Sample: Each voice a reconstruction stands behind.
    """
    return (voice for voice in voices if isinstance(voice, Sample))


def voice_channels(voice: VoiceUnion) -> Tuple[ChannelName, ...]:
    """The channels a voice sounds on.

    A sample sounds on the channels its reconstruction found frames for; a shape sounds wherever
    its envelopes make a frame, which is every channel once it writes one.

    Args:
        voice: The voice being placed.

    Returns:
        Tuple[ChannelName, ...]: The channels it sounds on, in channel order.
    """
    match voice:
        case Sample():
            return voice.reconstruction.playing_channels
        case Shape():
            return tuple(channel for channel in ChannelName.items() if voice.instructions(channel))


def voice_reference(voice: VoiceUnion, channel_name: ChannelName) -> int:
    """The value a voice's arpeggio is measured against on one channel.

    A sample carries the reference its conversion chose for that channel; a shape states the root
    the reader gave it. A row's transpose is the step from this, whichever kind it names.

    Args:
        voice: The voice being sounded.
        channel_name: The channel sounding it.

    Returns:
        int: The pitch, or the period, the voice rests at on that channel.
    """
    match voice:
        case Sample():
            return voice.reconstruction.initial_pitches[channel_name]
        case Shape():
            return voice.reference(channel_name)
