from typing import Optional

from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceUnion


def voice_kind(voice: VoiceUnion) -> VoiceKind:
    """Which of the two kinds a voice is, as the list marks it.

    Args:
        voice: The voice being listed.

    Returns:
        VoiceKind: The kind the row shows and its gestures follow from.
    """
    match voice:
        case Sample():
            return VoiceKind.SAMPLE
        case Instrument():
            return VoiceKind.INSTRUMENT


def column_takes(channel: Optional[ChannelName], kind: VoiceKind) -> bool:
    """Whether the column a cell stands in places a voice of this kind.

    A channel column sounds whatever it is given, so it takes either kind. The sample column
    spreads a voice over the channels it covers, which a recording states and a hand-written voice
    does not, so it takes a recording alone.

    Args:
        channel: The channel the column carries, ``None`` for the sample column.
        kind: The kind of the voice being placed.

    Returns:
        bool: Whether the column takes it.
    """
    if channel is not None:
        return True

    return kind.places_across_channels
